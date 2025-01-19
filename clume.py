import RPi.GPIO as GPIO
import time

# Konfigurasi pin GPIO
LED_PIN = 23  # GPIO17 (pin 11)

# Setup
GPIO.setmode(GPIO.BCM)  # Gunakan penomoran GPIO (BCM)
GPIO.setup(LED_PIN, GPIO.OUT)  # Atur GPIO sebagai output

# Nyalakan LED
while True:
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(2)  # LED menyala selama 5 detik

    GPIO.output(LED_PIN, GPIO.LOW)
    time.sleep(1)

# Bersihkan konfigurasi GPIO
GPIO.cleanup()