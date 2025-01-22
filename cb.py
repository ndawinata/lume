from obspy import read
from obspy.signal.freqattributes import peak_ground_motion

st = read()

tr = st[0]

tr.plot()
# st[0].plot()
# st[1].plot()
# st[2].plot()

# # Hapus respons instrumen untuk mendapatkan perpindahan
# tr.remove_response(output="DISP")  # Menghasilkan data dalam meter (perpindahan)
# tr.plot()
# st.plot()
# Pastikan data dalam satuan yang benar (misalnya, percepatan dalam m/s²)
# Jika perlu, lakukan konversi satuan sebelum analisis

# Tentukan parameter
delta = tr.stats.delta  # Interval sampling
freq = 1.0  # Frekuensi dalam Hz (sesuaikan dengan kebutuhan Anda)
damp = 0.1  # Faktor redaman (default)

# Hitung parameter ground motion
pga, max_disp, max_vel, max_acc = peak_ground_motion(tr.data, delta, freq, damp)

# Tampilkan hasil
print(f"PGA: {pga} m/s²")
print(f"Max Displacement: {max_disp} m")
print(f"Max Velocity: {max_vel} m/s")
print(f"Max Acceleration: {max_acc} m/s²")