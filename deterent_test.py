import board
import busio
import adafruit_mcp4725
from pydub import AudioSegment
import time

# Setup I2C and DAC
i2c = busio.I2C(board.SCL, board.SDA)
mcp = adafruit_mcp4725.MCP4725(i2c, address=0x60)

# Load MP3 and convert to raw samples
audio = AudioSegment.from_mp3("C:\Users\Sabelo Mathonzi\Desktop\EEE4113F\Dashboard_EEE4113F\scream-with-echo-46585.mp3")
audio = audio.set_channels(1)  # mono
audio = audio.set_frame_rate(8000)  # downsample to 8 kHz (I2C-friendly)
samples = audio.get_array_of_samples()

# Scale to 12-bit values (0–4095)
for sample in samples:
    value = int((sample + 32768) * (4095 / 65535))  # assuming 16-bit input
    mcp.raw_value = value
    time.sleep(1 / 8000)  # delay to match sample rate

print("Done playing through MCP4725")
