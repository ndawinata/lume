from fastapi import FastAPI, Request, WebSocket, BackgroundTasks
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
import board
import neopixel

# Konfigurasi pin GPIO
BUZZER_PIN = 23  # GPIO17 (pin 11)

# Setup
GPIO.setwarnings(False)  # Gunakan penomoran GPIO (BCM)

GPIO.setmode(GPIO.BCM)  # Gunakan penomoran GPIO (BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)  # Atur GPIO sebagai output

# NeoPixels must be connected to D10, D12, D18 or D21 to work.
PIXEL_PIN = board.D12


# The number of NeoPixels
NUM_PIXELS = 32

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
# GRB  : Green Red Blue
# GRBW : Green Red Blue White
ORDER = neopixel.GRB

# brightness(float) : between 0.0 and 1.0 where is 1.0 full brightness
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False, pixel_order=ORDER)


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


async def set_color(rgb):
    # Fungsi untuk mengatur warna lampu
    pixels.fill(rgb)
    pixels.show()

async def buzzer_on():
    # Fungsi untuk menyalakan buzzer
    GPIO.output(BUZZER_PIN, GPIO.HIGH)

async def buzzer_off():
    # Fungsi untuk mematikan buzzer
    GPIO.output(BUZZER_PIN, GPIO.LOW)

async def aman():
    # Kategori Aman: Lampu Hijau (Tidak ada Buzzer)
    await buzzer_on()
    await set_color((0, 255, 0))  # Hijau
    await asyncio.sleep(3)
    await buzzer_off()
    await set_color((0, 0, 0))

async def peringatan(durasi):
    # Kategori Peringatan: Lampu Kuning + Buzzer dengan ritme
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < durasi:
        # Kedip lambat
        await buzzer_on()
        await set_color((255, 255, 0))
        await asyncio.sleep(1)
        await buzzer_off()
        await set_color((0, 0, 0))
        await asyncio.sleep(1)

async def bahaya(durasi):
    # Kategori Bahaya: Lampu Merah + Buzzer dengan ritme cepat
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < durasi:
        # Kedip cepat
        await buzzer_on()
        await set_color((255, 0, 0))
        await asyncio.sleep(0.5)
        await buzzer_off()
        await set_color((0, 0, 0))
        await asyncio.sleep(0.5)

# warning tipe
    # suara dan lampu akan terus menyala looping sampai countdown habis + 20 detik
    # 3 hijau (aman) buzzer (0, 255, 0) buzzer t1 f1 t2 f1 t3 selesai
    # 4-5 orange (warning) (255, 255, 0) buzzer t0.5 f1.5 loop until countdown end
    # > 5 merah (danger) (255, 0, 0) buzzer t0.5 f0.5 loop until countdown end

async def warn(mmi, ot, R):
    ctd = round(R / 4)

    originTime = datetime.strptime(ot, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    current_datetime = datetime.now(timezone.utc)

    time_difference = (current_datetime - originTime).total_seconds()

    durasi = ctd - time_difference
    print(mmi, durasi, R)
    if durasi > 0:
        if mmi == 3:
            await aman()
        elif 3 < mmi < 6:
            await peringatan(durasi)
        elif mmi >= 6:
            await bahaya(durasi)


async def handle_output(d, jns):
    cfg = read_config()
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
    
    d['eew_id'] = djson['earthquake']['event']['id']
    
    if d['lat'] <= lat_max and d['lat'] >= lat_min and d['lon'] <= lon_max and d['lon'] >= lon_min:

        if th:
            if mag >= mag_th and MMI >= mmi_th and PGA >= pga_th:

                # warn(MMI, d['ot'], R)
                asyncio.create_task(warn(MMI, d['ot'], R))
                for connection in connections:
                    await connection.send_json(djson)
        else:
            # warn(MMI, d['ot'], R) 
            asyncio.create_task(warn(MMI, d['ot'], R))

            for connection in connections:
                await connection.send_json(djson)


async def filter_event(msg):
    dat = msg['data']
    cfg = read_config()
    test = cfg.getboolean('base', 'receive_test')

    dtime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    if test and msg['type'] == 'eew-test':

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