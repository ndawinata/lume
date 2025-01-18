import board
import neopixel

# Konfigurasi
PIXEL_PIN = board.D23  # GPIO23
NUM_PIXELS = 24        # Jumlah LED pada NeoPixel

# Inisialisasi NeoPixel
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, auto_write=False)

# Atur semua LED menjadi merah
pixels.fill((255, 0, 0))
pixels.show()