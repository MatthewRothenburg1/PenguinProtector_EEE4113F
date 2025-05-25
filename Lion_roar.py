import time
import board
import busio
import numpy as np
from adafruit_mcp4725 import MCP4725
from pydub import AudioSegment

# Initialize I2C bus and MCP4725 DAC
i2c = busio.I2C(board.SCL, board.SDA)
dac = MCP4725(i2c)

# Load the WAV file
audio = AudioSegment.from_wav("lion_growl.wav")

# Convert audio to raw samples (16-bit PCM)
samples = np.array(audio.get_array_of_samples())

# Normalize samples to 12-bit DAC range (0-4095)
# MCP4725 is a 12-bit DAC, unsigned
# WAV samples are signed 16-bit (-32768 to 32767)
samples_12bit = ((samples.astype(np.int32) + 32768) * 4095 // 65535).astype(np.uint16)

# Playback function
sample_rate = audio.frame_rate  # e.g., 44100 Hz
sample_delay = 1 / sample_rate  # Delay between samples

print("Playing audio...")

for sample in samples_12bit:
    dac.raw_value = sample
    time.sleep(sample_delay)

print("Playback finished.")
