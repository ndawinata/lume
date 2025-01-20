from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from starlette.websockets import WebSocketDisconnect
from contextlib import asynccontextmanager   
from fastapi.responses import RedirectResponse
from geopy.distance import geodesic
import websockets
import configparser
import json 
import asyncio
import subprocess
import asyncio
import math
import os
import asyncpg
import httpx
import uvicorn
import RPi.GPIO as GPIO
import time

# Konfigurasi pin GPIO
LED_PIN = 23  # GPIO17 (pin 11)

# Setup
GPIO.setwarnings(False)  # Gunakan penomoran GPIO (BCM)

GPIO.setmode(GPIO.BCM)  # Gunakan penomoran GPIO (BCM)
GPIO.setup(LED_PIN, GPIO.OUT)  # Atur GPIO sebagai output



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inisialisasi tugas pendengar WebSocket
    listener_task = asyncio.create_task(listen_to_external_server())
    try:
        # Mulai aplikasi
        print("Aplikasi mulai")
        yield  # Bagian ini memungkinkan aplikasi untuk melanjutkan eksekusi
    finally:
        # Bersihkan tugas ketika aplikasi berhenti
        listener_task.cancel()
        await listener_task
        print("Aplikasi berhenti")


app = FastAPI(lifespan=lifespan)

# Inisialisasi parser konfigurasi
config = configparser.ConfigParser()
config.read('config.cfg')

base_path = os.getcwd()

# Akses konfigurasi
source = 'simap.bmkg.go.id'
apiFeedback = "https://simap.bmkg.go.id/feedback"
lume_host = config['base']['lume_host']
lume_port = config['base']['lume_port']
nama = config['base']['name_device']
sender = None

base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
template_dir = os.path.join(base_dir, "templates")

templates = Jinja2Templates(directory=template_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Function to read configuration
def read_config():
    config = configparser.ConfigParser()
    config.read("config.cfg")
    return config


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def write_config(config):
    with open('config.cfg', 'w') as configfile:
        config.write(configfile)

def hitung_jarak(row, koordinat_A):
    koordinat_B = (row['lat'], row['lon'])
    
    return geodesic(koordinat_A, koordinat_B).kilometers

def pga_pred(R, M, depth):
    # Keluaran dalam gals
    dh = 0
    if depth < 15:
        dh = 1
    
    if depth <= 50 and M <= 5.3:
        # Akkar Boomer 2007
        PGA = (1.647 + 0.767 * M + 0.074 * M ** 2 + (-3.162 + 0.321 * M) * math.log10(math.sqrt(R ** 2 + 7.682 ** 2)))
        return 10 ** PGA
    else:
        # Zhao
        dist2 = math.sqrt(R ** 2 + depth ** 2)
        rzhao = dist2 + 0.0055 * math.exp(1.080 * M)
        ly = (1.101 * M - 0.00564 * dist2 - math.log(rzhao) + 0.01412 * (depth - 15) * dh + 1.111)
        
        if 22 < depth < 50 and 5.3 < M <= 7.2:
            ly += (2.607 - 0.528 * math.log(dist2))
        else:
            ly += (2.607 - 0.528 * math.log(dist2))
        
        PGA = math.exp(ly)
        return PGA

def mmi_worden(PGA):
    # Worden et al. (2021)
    if PGA <= 0.8:
        return 0
    if math.log10(PGA) <= 1.57:
        return round(1.78 + 1.55 * math.log10(PGA))
    else:
        return round(-1.6 + 3.70 * math.log10(PGA))

async def post_feed(d):
    cfg = read_config()
    lat = cfg['base']['lume_lat']
    lon = cfg['base']['lume_lon']
    feed = cfg.getboolean('base', 'feedback')
    if feed:
        try:
            # Prepare data for the POST request
            payload = {
                "receiveTime": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                "lat": lat,
                "lon": lon,
                "device": nama,
                "identifier": d['eew_id']
            }
            

            # Perform the async POST request
            async with httpx.AsyncClient() as client:
                response = await client.post(apiFeedback, json=payload, headers={"Content-Type": "application/json"})

            # Check the response
            if response.status_code == 200:
                print("Success send feedback")
            else:
                print(f"Failed send feedback with status code {response.status_code}: {response.text}")

        except Exception as e:
            print("Error send feedback:", e)
    
@app.get("/")
async def index(request: Request):
    cfg = read_config()
    lat = cfg['base']['lume_lat']
    lon = cfg['base']['lume_lon']
    r = cfg['base']['radius']

    return templates.TemplateResponse("dashboard.html", {'request':request, 'r':r, 'ur_lat':lat, 'ur_lon':lon, 'lok':find_location(lat, lon)['lokasi'], 'title':'LUME | Light for Urgent Mitigation of Earthquake'})
    
@app.post("/set_coor")
async def set_coor(data: dict):
    # Ubah nilai pada bagian base
    config['base']['lume_lat'] = data['ur_lat']  # Masukkan nilai baru untuk lat
    config['base']['lume_lon'] = data['ur_lon']  # Masukkan nilai baru untuk lon
    config['base']['radius'] = data['r'] # Masukkan nilai baru untuk radius

    # Tulis perubahan ke file config.cfg
    with open('config.cfg', 'w') as configfile:
        config.write(configfile)

    return data

@app.post("/setting")
async def set_setting(request: Request):
    form_data = await request.form()

    # Update konfigurasi dengan nilai yang dikirim dari form
    for section in config.sections():
        for key in config[section]:
            form_key = f"{section}_{key}"
            
            # Jika nilai adalah checkbox (true/false), periksa apakah form_data mengandung key
            if config[section][key].lower() in ["true", "false"]:
                # Jika ada di form_data, berarti checkbox dicentang (true)
                config[section][key] = "true" if form_key in form_data else "false"
            else:
                # Untuk input teks biasa
                if form_key in form_data:
                    config[section][key] = form_data[form_key]
    
    # Simpan perubahan ke file konfigurasi
    write_config(config)
    return RedirectResponse(url="/", status_code=303)

@app.get("/setting")
async def setting(request: Request):

    config_dict = {section: dict(config[section]) for section in config.sections()}
    return templates.TemplateResponse("setting.html", {'request':request, 'title':'LUME | Setting', 'config':config_dict})

@app.get("/rev_geocoding/{lat},{lon}")
def find_location(lat, lon):
    data = indonesia_data
    nearest_location = None
    min_distance = float("inf")
    
    for province in data:
        province_name = province['name']
        for regency in province.get('regencies', []):
            regency_name = regency['name']
            regency_coords = (regency['latitude'], regency['longitude'])
            
            # Hitung jarak dari koordinat input ke setiap kabupaten/kota
            distance = geodesic((lat, lon), regency_coords).kilometers
            if distance < min_distance:
                min_distance = distance
                nearest_location = f"{regency_name}-{province_name}"
    
    return {"lokasi":nearest_location if nearest_location else "Location not found"}


async def handle_output(d, jns):
    cfg = read_config()
    print('msk')
    th = cfg.getboolean('base', 'threshold')

    lat = float(cfg['base']['lume_lat'])
    lon = float(cfg['base']['lume_lon'])
    r = float(cfg['base']['radius'])
    lat_min = lat - r
    lat_max = lat + r
    lon_min = lon - r
    lon_max = lon + r

    mag = float(d['mag'])
    depth = float(d['depth'])
    R = geodesic((lat, lon), (float(d['lat']), float(d['lon']))).kilometers
    mag_th = float(cfg['threshold']['magnitude'])
    mmi_th = float(cfg['threshold']['mmi'])
    pga_th = float(cfg['threshold']['pga'])

    PGA = round(pga_pred(R, mag, depth), 2)

    MMI = mmi_worden(PGA)
    
    dd = {
        'data':d,
        'type':jns
    }


    djson = genOutput(dd)
    print('djson : ',djson)
    
    d['eew_id'] = djson['earthquake']['event']['id']
    
    if d['lat'] <= lat_max and d['lat'] >= lat_min and d['lon'] <= lon_max and d['lon'] >= lon_min:
        for i in range(5):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(2)  # LED menyala selama 5 detik

            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(1)

        if th:
            if mag >= mag_th and MMI >= mmi_th and PGA >= pga_th:

                djson['earthquake']['impact'] = {"mmi":MMI, "pga":PGA}

                for connection in connections:
                    await connection.send_json(djson)
        else:

            for connection in connections:
                await connection.send_json(djson)


async def filter_event(msg):
    print(msg)
    dat = msg['data']
    cfg = read_config()
    test = cfg.getboolean('base', 'receive_test')
    print('1')

    dtime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print('2')
    
    if test and msg['type'] == 'eew-test':
        print('3')

        d = {
            "eew_id": dat['identifier'],
            "dtime": dtime,
            "ot": dat["originTime"],
            "lat": float(dat['epicenterLat']),
            "lon": float(dat['epicenterLon']),
            "depth": float(dat['depth']),
            "mag": float(dat['magnitude'])

        }

        print('ll :  ', d)


        await handle_output(d, msg['type'])
    
    if msg['type'] == 'eew':
        d = {
            "eew_id": dat['identifier'],
            "dtime": dtime,
            "ot": dat["originTime"],
            "lat": float(dat['epicenterLat']),
            "lon": float(dat['epicenterLon']),
            "depth": float(dat['depth']),
            "mag": float(dat['magnitude'])

        }
        
        await handle_output(d, msg['type'])

        await post_feed(d)


# Load JSON file
with open('indonesia-region.min.json', 'r') as f:
    indonesia_data = json.load(f)


def genOutput(d):
    dat = d['data']
    id = datetime.strptime(dat['ot'], '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d%H%M%S")
    ot = datetime.strptime(dat['ot'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%dT%H:%M:%SZ")
    loc  = find_location(dat['lat'], dat['lon'])['lokasi']
    mag = dat['mag']
    lat = dat['lat']
    lon = dat['lon']
    depth = dat['depth']

    djson = {
        "earthquake": {
            "type": 'alert',
            "event": {
                "id": id,
                "localAddress": loc,
                "magnitude": mag,
                "latitude": lat,
                "longitude": lon,
                "depth": depth,
                "originTime": ot
            }
        }
    }


    return djson



connections = set()

async def listen_to_external_server():
    websocket_url = f"wss://{source}/ws_data"  # Replace with your WebSocket server URL
    retry_delay = 1  # Initial delay in seconds for retries

    while True:
        try:
            # Connect to the WebSocket server
            async with websockets.connect(websocket_url) as websocket:
                print("Connected to WebSocket server")
                for connection in connections:
                    # await connection.send_json({'data':True,'type':'ws_svr'})
                    await connection.send_json({'earthquake':{'type':'ws_svr','event':True}})
                retry_delay = 1  # Reset delay after a successful connection

                while True:
                    try:
                        # Listen for messages
                        message = await websocket.recv()
                        # print("Message received:", message)
                        # Process the message (e.g., pass it to your event handler)
                        await filter_event(json.loads(message))
                    except websockets.ConnectionClosed:
                        print("Connection closed. Attempting to reconnect...")
                        break  # Exit inner loop to reconnect
        except Exception as e:
            print(f"Failed to connect: {e}. Retrying in {retry_delay} seconds...")
            
            for connection in connections:
                # await connection.send_json({'data':False,'type':'ws_svr'})
                await connection.send_json({'earthquake':{'type':'ws_svr','event':False}})
            
            # Wait before retrying (with exponential backoff)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30 seconds

@app.websocket("/ws_data")
async def websocket_data(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    try:
        while True:
            # Menunggu pesan dari WebSocket, tetapi tidak digunakan di sini
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.remove(websocket)       

if __name__ == "__main__":
    uvicorn.run("main:app", host=lume_host, port=int(lume_port), reload=True)
    # uvicorn.run("lume:app", host=f"{lume_host}", port=int(lume_port), reload=True, log_level="warning")
    # uvicorn.run("lume:app", host=f"{lume_host}", port=int(lume_port), log_level="warning")
    # uvicorn.run("lume:app", host=f"{lume_host}", port=int(lume_port))