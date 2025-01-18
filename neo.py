
import time
import board
import neopixel
import sys

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

 
def wheel(pos):
	# Input a value 0 to 255 to get a color value.
	# The colours are a transition r - g - b - back to r.
	if pos < 0 or pos > 255:
		r = g = b = 0
	elif pos < 85:
		r = int(pos * 3)
		g = int(255 - pos * 3)
		b = 0
	elif pos < 170:
		pos -= 85
		r = int(255 - pos * 3)
		g = 0
		b = int(pos * 3)
	else:
		pos -= 170
		r = 0
		g = int(pos * 3)
		b = int(255 - pos * 3)
	return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)
 
 
def rainbow_cycle(wait):
	for j in range(255):
		for i in range(NUM_PIXELS):
			pixel_index = (i * 256 // NUM_PIXELS) + j
			pixels[i] = wheel(pixel_index & 255)
		pixels.show()
		time.sleep(wait)


def usage():
	print("usage python3 "+str(sys.argv[0])+" [options]")
	print("Options:")
	print("R/r : Red")
	print("G/g : Green")
	print("B/b : Blue")
	print("W/w : White")
	print("C/c : Cycle")


while True: 
	try:
		if len(sys.argv) == 2:
			if str(sys.argv[1]).lower() == "r":
				pixels.fill((255,0,0))
				pixels.show()
				time.sleep(1)

			elif str(sys.argv[1]).lower() == "g":
				pixels.fill((0,255,0))
				pixels.show()
				time.sleep(1)

			elif str(sys.argv[1]).lower() == "b":
				pixels.fill((0,0,255))
				pixels.show()
				time.sleep(1)

			elif str(sys.argv[1]).lower() == "w":
				pixels.fill((255,255,255))
				pixels.show()
				time.sleep(1)
			
			elif str(sys.argv[1]).lower() == "p":
				pixels.fill((128,0,128))
				pixels.show()
				time.sleep(1)
			
			elif str(sys.argv[1]).lower() == "o":
				pixels.fill((255,100,50))
				pixels.show()
				time.sleep(1)

			elif str(sys.argv[1]).lower() == "c":
				rainbow_cycle(0.001)  # rainbow cycle with 1ms delay per step

			else:
				usage()
				sys.exit()

		else:
			usage()
			sys.exit()

	except KeyboardInterrupt:
		print("Keyboard Exception.Exiting...")
		pixels.fill((0,0,0))
		pixels.show()
		sys.exit()
