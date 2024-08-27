import pygame

FRAME_WIDTH = 144
FRAME_HEIGHT = 108
FRAME_COUNT = 1533
VAR_INT_CHUNK_LEN = 5
FRAMERATE = 7

FRAME_PIX = FRAME_WIDTH * FRAME_HEIGHT
VAR_INT_MASK = 0x00
for _ in range(VAR_INT_CHUNK_LEN-1):
	VAR_INT_MASK = (VAR_INT_MASK << 1) | 0x01

class BitReader:
	def __init__(self, file):
		self.file = open(file, "rb")
		self.bitIndex = 0
		self.currentByte = int.from_bytes(self.file.read(1), byteorder='big', signed=False)
	def read(self, bitCount):
		if bitCount == 0:
			return 0x00
		if (self.bitIndex + bitCount) < 8:
			mask = 0x00
			for _ in range(bitCount):
				mask = (mask << 1) | 0x01
			mask = mask << (8 - self.bitIndex - bitCount)
			ret = (self.currentByte & mask) >> (8 - self.bitIndex - bitCount)
			self.bitIndex += bitCount
			return ret
		tmp = bitCount
		ret = 0x00
		mask = 0xFF >> self.bitIndex
		ret = (self.currentByte & mask)
		tmp -= (8-self.bitIndex)
		fullBytes = tmp // 8
		if fullBytes != 0:
			val = int.from_bytes(self.file.read(fullBytes), byteorder='big', signed=False)
			ret = (ret << (fullBytes * 8)) | val
			tmp -= fullBytes * 8
		self.currentByte = int.from_bytes(self.file.read(1), byteorder='big', signed=False)
		if tmp != 0:
			mask = 0xFF << (8 - tmp)
			val = (self.currentByte & mask) >> (8 - tmp)
			ret = (ret << tmp) | val
		self.bitIndex = tmp
		return ret

def encodeInt(val):
	scratch = val
	ret = 0x00
	length = 0
	while True:
		tmp = (scratch & VAR_INT_MASK) << 1
		ret = (ret << VAR_INT_CHUNK_LEN) | tmp
		scratch = scratch >> (VAR_INT_CHUNK_LEN-1)
		length += VAR_INT_CHUNK_LEN
		if scratch == 0:
			break
		ret |= 0x01
	return (ret, length)
def decodeInt(reader):
	ret = 0
	length = 0
	while True:
		val = reader.read(VAR_INT_CHUNK_LEN)
		ret = ret | ( (val>>1) << length )
		length += VAR_INT_CHUNK_LEN-1
		if (val & 0x01) == 0:
			break
	return ret

#=================================

pygame.init()
# Graphics init
screen = pygame.display.set_mode( (FRAME_WIDTH, FRAME_HEIGHT) )
clock = pygame.time.Clock()
# Sound init
pygame.mixer.init()
pygame.mixer.music.load("song.ogg")
pygame.mixer.music.set_volume(0.7)

reader = BitReader("encodedImages.bin")
totalFrames = 0 # how many frames have been displayed

running = True
pygame.mixer.music.play()
while running:
	screen.fill(0)
	xPos = 0
	yPos = 0
	color = reader.read(1)
	direction = reader.read(1)
	compressedFrameData = []

	frameCount = 0 # How many pixels have been loaded for the frame
	while frameCount != FRAME_PIX:
		count = decodeInt(reader)
		frameCount += count
		compressedFrameData.append(count)
	totalFrames += 1

	if direction == 1:
		for chunk in compressedFrameData:
			while chunk != 0:
				screen.set_at( (xPos,yPos), ((0,0,0) if color == 0 else (255,255,255)) )
				xPos += 1
				if xPos >= FRAME_WIDTH:
					xPos = 0
					yPos += 1
				chunk -= 1
			color = 0 if color == 1 else 1
	else:
		for chunk in compressedFrameData:
			while chunk != 0:
				screen.set_at( (xPos,yPos), ((0,0,0) if color == 0 else (255,255,255)) )
				yPos += 1
				if yPos >= FRAME_HEIGHT:
					yPos = 0
					xPos += 1
				chunk -= 1
			color = 0 if color == 1 else 1
	pygame.display.flip()
	clock.tick(FRAMERATE)

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False
	if totalFrames >= FRAME_COUNT:
		running = False

pygame.mixer.music.stop()
pygame.quit()