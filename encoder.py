import os
import math
from PIL import Image

FRAME_COUNT = 1533
FRAME_PIX = 15552

VAR_INT_CHUNK_LEN = 5 # 3 bits per var chunk, bits 01 are part of the number, 2 is the continue flag (set to 0 to end number)
VAR_INT_MASK = 0x00
for _ in range(VAR_INT_CHUNK_LEN-1):
	VAR_INT_MASK = (VAR_INT_MASK << 1) | 0x01

class BitReader:
	def __init__(self, file):
		self.file = open(file, "rb")
		self.bitIndex = 0
		self.currentByte = int.from_bytes(self.file.read(1), byteorder='big', signed=False)

	# Read X number of bits
	def read(self, bitCount):
		if bitCount == 0:
			return 0x00

		# We only stay within the current bit
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

		# Read beginning bits from the current byte
		mask = 0xFF >> self.bitIndex
		ret = (self.currentByte & mask)
		tmp -= (8-self.bitIndex)

		# Read whole bytes
		fullBytes = tmp // 8
		if fullBytes != 0:
			val = int.from_bytes(self.file.read(fullBytes), byteorder='big', signed=False)
			ret = (ret << (fullBytes * 8)) | val
			tmp -= fullBytes * 8

		self.currentByte = int.from_bytes(self.file.read(1), byteorder='big', signed=False) # Get new byte (if we have nothing left to read, bitIndex will be set to 0)
		# Read ending bits
		if tmp != 0:
			mask = 0xFF << (8 - tmp)
			val = (self.currentByte & mask) >> (8 - tmp)
			ret = (ret << tmp) | val

		self.bitIndex = tmp # tmp will always be the new bitIndex for the current byte
		return ret

# Encode to a var length int
# Returns (val, bit length)
def encodeInt(val):
	scratch = val
	ret = 0x00
	length = 0
	while True:
		tmp = (scratch & VAR_INT_MASK) << 1 # Shift by 1 to make room for the flag
		ret = (ret << VAR_INT_CHUNK_LEN) | tmp
		scratch = scratch >> (VAR_INT_CHUNK_LEN-1)
		length += VAR_INT_CHUNK_LEN
		if scratch == 0:
			break
		# Still more to encode, set flag
		ret |= 0x01

	return (ret, length)
# Decode a variable int given a BitReader
# Returns intVal
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

# Calculate distance between 2 points in 3d space
def distance(p1, p2):
	a = math.pow( (p1[0] - p2[0]), 2 )
	b = math.pow( (p1[1] - p2[1]), 2 )
	c = math.pow( (p1[2] - p2[2]), 2 )
	return math.sqrt(a + b + c)

def closestColor(color):
	black = (16, 128, 128)
	white = (235, 128, 128)
	blackDist = abs( distance(color, black) )
	whiteDist = abs( distance(color, white) )
	return (0 if blackDist < whiteDist else 1)



print("Analyzing frames...")
frames = os.listdir("./imgs")

globalEncoding = []


for i, img in enumerate(frames):
	print(f"Frame {i}")
	pix = Image.open( os.path.join("./imgs", img) ).convert('YCbCr') #Load image into YUV (supposedly closer to human perception)
	im = pix.load()
	encodedHoriz = []
	encodedVert = []
	# (Color, length)
	# 0=black, 1=white

	# Go through each pixel and map to black or white
	count = 0 #How long the current run is
	currentColor = 0 #Color we are counting

	#Go through every pixel horizontally (split into individual channels)
	for y in range(pix.size[1]):
		for x in range(pix.size[0]):
			color = closestColor(im[x,y])
			if color == currentColor:
				count += 1
			else:
				if count != 0:
					encodedHoriz.append( (count, currentColor) )
				currentColor = color
				count = 1 # Count starts at 1 now because we have found a different color pixel
	# Append the last data set to encoded
	if count != 0:
		encodedHoriz.append( (count, currentColor) )


	count = 0 #How long the current run is
	currentColor = 0 #Color we are counting
	#Go through every pixel vertically (split into individual channels)
	for x in range(pix.size[0]):
		for y in range(pix.size[1]):
			color = closestColor(im[x,y])
			if color == currentColor:
				count += 1
			else:
				if count != 0:
					encodedVert.append( (count, currentColor) )
				currentColor = color
				count = 1 # Count starts at 1 now because we have found a different color pixel
	# Append the last data set to encoded
	if count != 0:
		encodedVert.append( (count, currentColor) )

	# Determine the more efficient encoding
	vertSize = 0
	horizSize = 0
	for c in encodedVert:
		_, length = encodeInt(c[0])
		vertSize += length

	for c in encodedHoriz:
		_, length = encodeInt(c[0])
		horizSize += length
	if vertSize < horizSize:
		globalEncoding.append( (0, encodedVert) )
	else:
		globalEncoding.append( (1, encodedHoriz) )
	pix.close()


'''
# Save data with 2byte encoding to unique files
for i, chunk in enumerate(globalEncoding):
	file = open( os.path.join("encoded", f"{i:04}.bin"), "wb" )
	for c in chunk[1]:
		val = (c[0] << 2) | (c[1] << 1) | chunk[0]
		file.write( val.to_bytes(3, byteorder='big', signed=False) )
	file.close()

# Load encoded data from files instead of recalculating
print("Loading frame data...")
for b in os.listdir("./encoded"):
	encoded = []
	with open( os.path.join("encoded", b), "rb" ) as f:
		while( bytes := f.read(3) ):
			num = int.from_bytes( bytes, byteorder="big", signed=False)
			color = (num & 0x02) >> 1
			direction = num & 0x01
			count = num >> 2
			encoded.append( (count, color) )
	globalEncoding.append( (direction, encoded) )
'''

# Write encoded data to file
print("Encoding to file...")

scratch = 0x00 # Build the value for the fullbytes to be written
scratchLen = 0 # How many bits are currently in scratch
saveBits = 0x00 # Bits that dont quite fit into a full byte
saveBitsLen = 0 # How many bits are in saveBits

file = open("encodedImages.bin", "wb")
for e in globalEncoding:
	for i, chunk in enumerate(e[1]):
		# Update scratch and saved values
		scratch = saveBits
		scratchLen = saveBitsLen
		saveBits = 0x00
		saveBitsLen = 0

		if i == 0: #First chunk, add color and direction flags
			scratch = scratch << 2
			scratch |= (chunk[1] << 1) | e[0]
			scratchLen += 2

		# encode length to bits
		countBits, countLen = encodeInt(chunk[0])
		scratch = scratch << countLen
		scratch |= countBits
		scratchLen += countLen
		# Check for dangling bits
		if (scratchLen % 8) != 0:
			saveBitsLen = scratchLen % 8
			mask = 0xFF >> (8-saveBitsLen)
			saveBits = scratch & mask
			scratch = scratch >> saveBitsLen
		fullBytes = scratchLen // 8
		if fullBytes != 0:
			file.write( scratch.to_bytes(fullBytes, byteorder='big', signed=False) )

# Write final bits (if needed)
if saveBitsLen != 0:
	saveBits = saveBits << (8-saveBitsLen)
	file.write( saveBits.to_bytes(byteorder='big', signed=False) )
file.close()

# Verify data matches once decoded
print("Sanity check...")
globalDecoding = []
index = 0

reader = BitReader("encodedImages.bin")
while index < FRAME_COUNT:
	decoding = []
	color = 0
	direction = 0
	frameCount = 0
	while frameCount != FRAME_PIX:
		if frameCount == 0: #First pixel of the frame, need to get color flag
			color = reader.read(1)
			direction = reader.read(1)

		count = decodeInt(reader)
		frameCount += count # Update total number of pixels countet
		decoding.append( (count, color) ) # Add new chunk to decoding
		if frameCount > FRAME_PIX: # Check for errors
			print(f"{globalEncoding[index]}\n{decoding}" )
			print(f"{index} {frameCount}")
			print("ERROR")
			exit()
		color = 1 if color==0 else 0 # Update color
	for enc, dec in zip(globalEncoding[index][1], decoding):
		if (enc[0] != dec[0]) or (enc[1] != dec[1]) or (globalEncoding[index][0] != direction):
			print(f"Mismatch! {enc} {dec}")
			exit()
	print(f"Check {index} passed")
	index += 1
