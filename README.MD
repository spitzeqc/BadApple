# Bad Apple (but its on a floppy disk)

## Setup
1. Install Pillow and PyGame
	- `pip install pillow pygame`
2. Compressing the video
	- Download [this video](https://youtu.be/FtutLA63Cp8)
	- Compress to 7FPS and 144p using `ffmpeg -i <input.file> -filter:v fps=7 -filter:v scale=144:-1 7fps.webm`
3. Extract frame data
	- Make a directory named `imgs`
	- Run `ffmpeg -i 7fps.webm imgs/frame%04d.png`
4. Run the encoder
	- `python encoder.py`
	- NOTE: if the encoder appears to be hanging or crashing during the "Sanity Check" phase, verify `FRAME_COUNT` and `FRAME_PIX` constants are accurate for your video
5. Compress the audio track enough to fit onto the disk
	- `ffmpeg -i 7fps.webm -c:a libvorbis -ab 32k -ar 22050 -vn song.ogg`
	- NOTE: the file must be called "song.ogg", or the player program must be updated with the new name
6. Run the player
	- `python player.py`
