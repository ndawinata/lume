from obspy import read, UTCDateTime, Stream
from obspy.clients.fdsn import Client
import sys, os, glob
import shutil
from obspy.geodetics import locations2degrees
from obspy.geodetics import degrees2kilometers
import matplotlib.pyplot as plt
from obspy import read_inventory
import time

print(sys.argv)
t0 = UTCDateTime(sys.argv[1])
t1 = UTCDateTime(sys.argv[2])
dirf = sys.argv[3]
late = float(sys.argv[4])
longe = float(sys.argv[5])
print(dirf)
if not os.path.isdir(dirf):
    os.mkdir(dirf)
    print(f"Directory '{dirf}' created.")

if not os.path.isdir(os.path.join(dirf, "plot")):
    os.mkdir(os.path.join(dirf, "plot"))
    print(f"Subdirectory 'plot' created in '{dirf}'.")

file_path = os.path.join(dirf, "hasil.txt")

file = open(file_path, "w")
file.write("Kode Lat Lon PGA-EW PGA-NS PGA-UD DIST(km)\n")
file.close()

#Membaca data stasiun dari file data.txt
with open('sta_jabar_acc.txt', 'r') as file:
    sta = file.readlines()

#Memisahkan setiap baris menjadi daftar
sta = [s.split() for s in sta]
file = open(file_path, "a")

#client = Client("http://localhost:8080/")
#client = Client("http://172.19.3.212:8080/")
client = Client("http://202.90.199.206:8080/")
stream = Stream()
dist = 10000

for s in sta:
    if dist > 200000:
        continue
    ff = glob.glob(os.path.join(dirf, f'{s[0]}_*.mseed'))
    if ff:
        continue
    try:
        try:
            st = client.get_waveforms("IA", s[0], "*", "HN*", t0, t1)
        except:
            st = client.get_waveforms("IA", s[0], "*", "EN*", t0, t1)
    except:
        try:
            try:
                st = client.get_waveforms("IA", s[0], "*", "SLZ", t0, t1)
            except:
                st = client.get_waveforms("IA", s[0], "*", "ACZ", t0, t1)
        except:
            print(s, 'No Data')
            continue

    st.detrend("demean")
    st.merge(fill_value=0)
    
    if st.count() == 0:
        continue

    try:
        # Mendapatkan inventory dari URL
        inv = read_inventory(f'http://202.90.199.206:8080/fdsnws/station/1/query?station={s[0]}&level=response&nodata=404')
        inv = inv[0][0][0].response.instrument_sensitivity.value
        print(inv)
    except AttributeError:
        print(f"Error retrieving instrument sensitivity for station {s[0]}. Skipping to the next station.")
        continue  # Jika error, lanjut ke stasiun berikutnya

    for i in range(len(st)):
        st[i].data = (st[i].data / inv) * 100 #intensity dikali, accelero dibagi data/inv
    
    E = st.select(channel='??E')
    dist += 5000
    
    if E.count() == 0:
        ampE = "N/A"
    else:
        ampE = str(round(max(abs(E[0].data)), 5))
    
    N = st.select(channel='??N')
    
    if N.count() == 0:
        ampN = "N/A"
    else:
        ampN = str(round(max(abs(N[0].data)), 5))
    
    Z = st.select(channel='??Z')
    
    if Z.count() == 0:
        ampZ = "N/A"
    else:
        ampZ = str(round(max(abs(Z[0].data)), 5))
        Z[0].stats.distance = dist
        stream += Z
    
    with open(file_path, "a") as file:
        file.write("{} {} {} {} {} {}\n".format(s[0], s[1], s[2], ampE, ampN, ampZ))
    print(f"{s[0]} data processed and saved.")
    st.write(os.path.join(dirf, f'{s[0]}.mseed'))
    st.plot(outfile=os.path.join(dirf, 'plot', f'{s[0]}.png'))

file.close()

#plt.title("Stream Accelerograph")
stream.plot(equal_scale=False, type='section', offset_min=0, offset_max=200000, orientation='horizontal')

# Move the hasil.txt file to the target directory
destination_path = os.path.join(dirf, "hasil_{dirf}.txt")

if os.path.isdir(dirf):
    shutil.move(file_path, destination_path)
    print(f"File 'hasil_{dirf}.txt' moved to {destination_path}")
else:
    print(f"Error: Destination directory '{dirf}' does not exist.")