import numpy as np
from obspy import Trace, Stream, UTCDateTime

# Parameter
sampling_rate = 100.0  # Hz
duration = 10.0        # detik
n_samples = int(sampling_rate * duration)
times = np.linspace(0, duration, n_samples, endpoint=False)

# Buat data sinusoidal
frequency = 1.0  # Hz
amplitude = 1.0
data = amplitude * np.sin(2 * np.pi * frequency * times)

print(data)

trace = Trace(data=data)
trace.stats.sampling_rate = sampling_rate
trace.stats.starttime = UTCDateTime.now()
trace.stats.station = "DUMY"  # Nama stasiun fiktif

stream = Stream(traces=[trace])

stream.plot()