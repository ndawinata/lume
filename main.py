from websockets.exceptions import ConnectionClosedError, InvalidStatusCode
from fastapi import FastAPI, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager   
from fastapi.responses import RedirectResponse
from geopy.distance import geodesic
import xml.etree.ElementTree as ET
# from SetDB import Database
# from typing import Set
import websockets
import configparser
import pandas as pd
import json 
import threading
import asyncio
import subprocess
import platform
import asyncio
import serial
import math
import time
import os
import asyncpg
import httpx
import xmltodict
import socket
import uvicorn


app = FastAPI()



# Inisialisasi parser konfigurasi
config = configparser.ConfigParser()
config.read('config.cfg')

base_path = os.getcwd()

# Akses konfigurasi
source = 'simap.bmkg.go.id'
apiFeedback = "https://simap.bmkg.go.id/feedback"
unirec_host = config['base']['unirec_host']
unirec_port = config['base']['unirec_port']
nama = config['base']['name_device']
sender = None

base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
template_dir = os.path.join(base_dir, "templates")

templates = Jinja2Templates(directory=template_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


if config.getboolean('output', 'serial'):
    sender = serial.Serial(f"{config['serial']['com_port']}", baudrate=config['serial']['baudrate'], timeout=1)
    time.sleep(2)

# Function to read configuration
def read_config():
    config = configparser.ConfigParser()
    config.read("config.cfg")
    return config

def xml_to_json(xml_string):
    try:
        # Parse the XML into a dictionary
        dict_data = xmltodict.parse(xml_string)
        
        # Convert the dictionary to JSON
        json_data = json.dumps(dict_data, indent=4)
        return json_data
    except Exception as e:
        print(f"Error converting XML to JSON: {e}")
        return None

# Lifespan with external server listener and heartbeat
@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = read_config()
    hbrt = config.getboolean('output', 'heartbeat')
    host = cfg["heartbeat"]["host"]
    port = cfg["heartbeat"]["port"]
    interval = int(cfg["heartbeat"]["interval"])
    
    # Start external server listener
    listener_task = asyncio.create_task(listen_to_external_server())
    
    # Initialize heartbeat_task to None
    heartbeat_task = None

    # Start heartbeat task
    if hbrt:
        heartbeat_task = asyncio.create_task(send_heartbeat(host, port, interval))
    try:
        yield  # Wait until the server stops
    finally:
        # Cancel both tasks when shutting down
        listener_task.cancel()
        
        try:
            await listener_task
        except asyncio.CancelledError:
            print("External server listener was canceled during shutdown.")
        
        # Cancel heartbeat task if it was started
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                print("Heartbeat task was canceled during shutdown.")
        

app.router.lifespan_context = lifespan

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def startup():
    print("Application startup")
    # Logika untuk membuat pool, misalnya:
    await db.create_pool()

async def shutdown():
    print("Application shutdown")
    # Logika untuk menutup pool, misalnya:
    await db.close_pool()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

def read_config():
    config = configparser.ConfigParser()
    config.read('config.cfg')
    return config

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
    lat = cfg['base']['unirec_lat']
    lon = cfg['base']['unirec_lon']
    feed = cfg.getboolean('base', 'feedback')
    if feed:
        try:
            # Prepare data for the POST request
            payload = {
                "receiveTime": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
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
    lat = cfg['base']['unirec_lat']
    lon = cfg['base']['unirec_lon']
    r = cfg['base']['radius']
    gui = config.getboolean('output', 'gui')

    if gui:
        return templates.TemplateResponse("dashboard.html", {'request':request, 'r':r, 'ur_lat':lat, 'ur_lon':lon, 'lok':find_location(lat, lon)['lokasi'], 'title':'UniRec | Universal Receiver EEWS'})
    else:
        return templates.TemplateResponse("404.html", {'request':request})
        
@app.post("/set_coor")
async def set_coor(data: dict):
    # Ubah nilai pada bagian base
    config['base']['unirec_lat'] = data['ur_lat']  # Masukkan nilai baru untuk lat
    config['base']['unirec_lon'] = data['ur_lon']  # Masukkan nilai baru untuk lon
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
    return templates.TemplateResponse("setting.html", {'request':request, 'title':'UniRec | Setting', 'config':config_dict})

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


def gen_point(d):
    points_json = config.get("point_monitor","points")

    points = json.loads(points_json)
    dd = []

    for point in points:
        R = geodesic((d['lat'], d['lon']),(point['lat'],point['lon'])).kilometers
        pga = pga_pred(R, d['mag'], d['depth'])
        mmi = mmi_worden(pga)


        dd.append({
            "name":point['name'],
            "lat":point['lat'],
            "lon":point['lon'],
            "pga":round(pga, 2),
            "mmi":mmi
        })
    return dd

async def handle_output(d, jns):
    cfg = read_config()
    eew_alarm = cfg['alarm']['eew_alarm']
    pgn_alarm = cfg['alarm']['pgn_alarm']

    speaker = cfg.getboolean('output', 'speaker')
    pst = cfg.getboolean('output', 'post2http')
    th = cfg.getboolean('base', 'threshold')
    multipoint = cfg.getboolean('base', 'multipoint')
    tcp = cfg.getboolean('output', 'post2tcp')

    lat = float(cfg['base']['unirec_lat'])
    lon = float(cfg['base']['unirec_lon'])
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


    dat = genOutput(dd)
    djson = dat[0]
    dxml = dat[1]

    if jns == 'pgn' or jns == 'pgn-test' :
        d['pgn_id'] = djson['earthquake']['event']['id'] 
    if jns == 'eew' or jns == 'eew-test' :  
        d['eew_id'] = djson['earthquake']['event']['id']

    if djson['earthquake']['type'] == 'alert' and multipoint:
        multipoints = gen_point(d)
        
        djson['earthquake']['multipoint'] = multipoints
        dxml = json_to_xml_point(djson['earthquake'], "earthquake")
    
    serial = config.getboolean('output', 'serial')
    if d['lat'] <= lat_max and d['lat'] >= lat_min and d['lon'] <= lon_max and d['lon'] >= lon_min:
        if th:
            if mag >= mag_th and MMI >= mmi_th and PGA >= pga_th:

                await save_event(d, jns)

                djson['earthquake']['impact'] = {"mmi":MMI, "pga":PGA}

                if speaker:
                    if jns == 'pgn' or jns == 'pgn-test':
                        subprocess.Popen(["aplay", pgn_alarm])
                    if jns == 'eew' or jns == 'eew-test':
                        subprocess.Popen(["aplay", eew_alarm])
                if pst:
                    await post2http(djson, dxml)
                if serial:
                    if jns == 'eew' or jns == 'eew-test':
                        text = f"{jns},{d['eew_id']},{d['dtime']},{d['ot']},{d['lat']},{d['lon']},{d['depth']},{d['mag']},{PGA},{MMI}"
                        sender.write(text.encode('utf-8'))
                    if jns == 'pgn' or jns == 'pgn-test':
                        text = f"{jns},{d['pgn_id']},{d['dtime']},{d['ot']},{d['lat']},{d['lon']},{d['depth']},{d['mag']},{PGA},{MMI}"
                        sender.write(text.encode('utf-8'))
                if tcp:
                    await post2tcp(djson, dxml)

                for connection in connections:
                    await connection.send_json(djson)
        else:
            await save_event(d, jns)
            if speaker:
                if jns == 'pgn' or jns == 'pgn-test':
                    subprocess.Popen(["aplay", pgn_alarm])
                if jns == 'eew' or jns == 'eew-test':
                    subprocess.Popen(["aplay", eew_alarm])
            if pst:
                await post2http(djson, dxml)
            if serial:
                if jns == 'eew' or jns == 'eew-test':
                    text = f"{jns},{d['eew_id']},{d['dtime']},{d['ot']},{d['lat']},{d['lon']},{d['depth']},{d['mag']}"
                    sender.write(text.encode('utf-8'))
                if jns == 'pgn' or jns == 'pgn-test':
                    text = f"{jns},{d['pgn_id']},{d['dtime']},{d['ot']},{d['lat']},{d['lon']},{d['depth']},{d['mag']}"
                    sender.write(text.encode('utf-8'))
            if tcp:
                await post2tcp(djson, dxml)

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
    
    if test and msg['type'] == 'pgn-test':
        d = {
            "pgn_id": dat['eventPgn_id'],
            "dtime": dtime,
            "ot": dat["ot"],
            "lat": float(dat['epicLat']),
            "lon": float(dat['epicLon']),
            "depth": float(dat['depth']),
            "mag": float(dat['mag'])

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

    if msg['type'] == 'pgn':
        d = {
            "pgn_id": dat['eventPgn_id'],
            "dtime": dtime,
            "ot": datetime.strptime(dat["ot"], "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S"),
            "lat": float(dat['epicLat']),
            "lon": float(dat['epicLon']),
            "depth": float(dat['depth']),
            "mag": float(dat['mag'])

        }

        await handle_output(d, msg['type'])

# Load JSON file
with open('indonesia-region.min.json', 'r') as f:
    indonesia_data = json.load(f)

def json_to_xml_with_version(json_data):
    """Konversi JSON ke XML dengan header versi XML."""
    xml_body = xmltodict.unparse(json_data, pretty=True)
    # xml_header = '<?xml version="1.0" encoding="UTF-8"?>'
    # return f"{xml_header}\n{xml_body}"
    return f"{xml_body}"

def json_to_xml_point(json_obj, root_name):
    root = ET.Element(root_name)
    for key, value in json_obj.items():
        if isinstance(value, dict):
            child = ET.SubElement(root, key)
            for sub_key, sub_value in value.items():
                ET.SubElement(child, sub_key).text = str(sub_value)
        elif isinstance(value, list):
            list_parent = ET.SubElement(root, key)
            for item in value:
                list_item = ET.SubElement(list_parent, "point")
                for sub_key, sub_value in item.items():
                    ET.SubElement(list_item, sub_key).text = str(sub_value)
        else:
            ET.SubElement(root, key).text = str(value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")



def genOutput(d):
    dat = d['data']
    tipe = 'report'
    id = datetime.strptime(dat['ot'], '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d%H%M%S")
    ot = datetime.strptime(dat['ot'], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%dT%H:%M:%SZ")
    loc  = find_location(dat['lat'], dat['lon'])['lokasi']
    mag = dat['mag']
    lat = dat['lat']
    lon = dat['lon']
    depth = dat['depth']

    if d['type'] == 'eew' or d['type'] == 'eew-test':
        tipe = 'alert'
    if d['type'] == 'pgn' or d['type'] == 'pgn-test':
        tipe = 'report'

    djson = {
        "earthquake": {
            "type": tipe,
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

    xml_data = json_to_xml_with_version(djson)

    return [djson, xml_data]



connections = set()

async def listen_to_external_server():
    websocket_url = f"wss://{source}/ws_data"  # Replace with your WebSocket server URL
    retry_delay = 1  # Initial delay in seconds for retries
    cfg = read_config()
    warn = cfg.getboolean('base', 'warn_disconnect')
    disconalarm = f'{base_path}/static/sound/disconnect.wav'

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
            if warn:
                subprocess.Popen(["aplay", disconalarm])
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
    uvicorn.run("main:app", host=unirec_host, port=int(unirec_port), reload=True)
    # uvicorn.run("unirec:app", host=f"{unirec_host}", port=int(unirec_port), reload=True, log_level="warning")
    # uvicorn.run("unirec:app", host=f"{unirec_host}", port=int(unirec_port), log_level="warning")
    # uvicorn.run("unirec:app", host=f"{unirec_host}", port=int(unirec_port))