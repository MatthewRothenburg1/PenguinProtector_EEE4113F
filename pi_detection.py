#!/usr/bin/env python3
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import RPi.GPIO as GPIO
import requests
import io
import time
import cv2
import subprocess
import threading
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

# === Configuration ===
PIR_PIN = 22
BUTTON_PIN = 27

SERVER_POLL_TIME = 0.5


#SERVER_URL = "http://192.168.3.146:8080"  # Local testing server
SERVER_URL = "https://flask-fire-837838013707.africa-south1.run.app"  # For deployment


def get_network_info():
    try:
        # Get IP address of wlan0
        ip = subprocess.check_output("hostname -I", shell=True).decode().split()[0]

        # Get SSID
        ssid = subprocess.check_output("iwgetid -r", shell=True).decode().strip()

        info_text = f"SSID = {ssid}\nIP = {ip}"

        return info_text
    except Exception as e:
        return "No network info"


# === Deterrent Stub ===
def deterrent():
    print("Deterrent triggered!")

#Take photo
def take_photo():
    # Capture photo
    frame = picam2.capture_array()
    return frame

# === Upload Image ===
def upload_image(frame):
    _, jpeg = cv2.imencode(".jpg", frame)
    image_bytes_io = io.BytesIO(jpeg.tobytes())
    response = requests.post(
        f"{SERVER_URL}/upload_to_vision",
        files={"file": ("photo.jpg", image_bytes_io.getvalue(), "image/jpeg")}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print("Image upload failed:", response.text)
        return None


def fetchStreamState():
    try:
        response = requests.get(f"{SERVER_URL}/get_streaming_state")
        if response.status_code == 200:
            data = response.json()
            print("Streaming state:", data)
        else:
            print(f"Failed to get data. Status code: {response.status_code}")
    except requests.RequestException as e:
        print("Error:", e)
    return data

def uploadToStream(frame):
    _, jpeg = cv2.imencode(".jpg", frame)
    image_bytes_io = io.BytesIO(jpeg.tobytes())
    response = requests.post(
        f"{SERVER_URL}/upload_to_stream",
        files={"file": ("photo.jpg", image_bytes_io.getvalue(), "image/jpeg")}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print("Image upload failed:", response.text)
        return None

def on_PIR():
    frame = take_photo()
    result = upload_image(frame)
    if result and "ID" in result:
        response_id = result["ID"]
        print(f"Image uploaded with ID: {response_id}")
        print(result)
        if result and result.get("detection") == True:
            deterrent()
            triggered = "true"

            # Record video only if animal was detected
            
            video_path = "/tmp/motion_video.h264"
            mp4_path = "/tmp/motion_video.mp4"

            encoder = H264Encoder()
            output = FileOutput(video_path)

            picam2.start_recording(encoder, output)
            time.sleep(5)
            picam2.stop_recording()

            # Convert to MP4 using MP4Box
            subprocess.run(["MP4Box", "-add", video_path, mp4_path], check=True)

            # Upload video
            upload_video(mp4_path, response_id, triggered)
            update_Oled("Upload Complete")

        else:
            print("No animal detected. Skipping video. Starting cooldown...")
            triggered = "false"
    else:
        print("Skipping video upload due to failed image upload.")
    PIR_STATE = False
    time.sleep(2)


# === Upload Video ===
def upload_video(path, ID, triggered):
    with open(path, 'rb') as f:
        video_bytes = f.read()

    # Send video as bytes with correct content type
    response = requests.post(
        f"{SERVER_URL}/upload_video",
        data={"ID": ID, "deterrent": triggered},
        files={
            "file": ("motion_video.mp4", video_bytes, "video/mp4")
        }
    )

    if response.status_code == 200:
        print("Video uploaded successfully:", response.json())
    else:
        print("Video upload failed:", response.text)


def clear_Oled():
    draw.rectangle((0, 0, oled_screen.width, oled_screen.height), outline=0, fill=0)
    oled_screen.display(oled_image)

def textToOled(text):
    draw.text((10, 10), text, font=font, fill=255)
    oled_screen.display(oled_image)

print("Starting up...")
print("Beggining setup...")


# Initialize the I2C connection to the OLED
oled_i2c = i2c(port=1, address=0x3C)
oled_screen = ssd1306(oled_i2c)


oled_image = Image.new("1", oled_screen.size)
draw = ImageDraw.Draw(oled_image)
font = ImageFont.load_default()
oled_screen.clear()
textToOled("Starting up...")

print("Oled Initialised")

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)



print("Initialisng Camera")

picam2 = Picamera2()
picam2.start()
time.sleep(1)  # Warm-up
textToOled("Camera Initialised")

time.sleep(0.5)

prev_time_stream = 0
dots = 0
while(GPIO.input(BUTTON_PIN) == GPIO.HIGH):
    oled_screen.clear()
    network_info = get_network_info()
    textToOled(network_info)
    for i in range(dots):
        textToOled(".")
    dots += 1
    if(dots > 3):
        dots = 0
    textToOled("Press Button to arm")

    print(network_info)
    time.sleep(0.5)

textToOled("Starting Detction")
time.sleep(0.5)


try:
    while True:

        current_time = time.time()

        if(GPIO.input(PIR_PIN) == GPIO.HIGH):
            on_PIR()
        
        #if(current_time - prev_time_stream > 30):
        #    stream_state = fetchStreamState()
        #    while(stream_state):    
        #        stream_state = fetchStreamState()
        #        frame = take_photo()
        #        uploadToStream(frame)
        #    prev_time_stream = current_time


            
except KeyboardInterrupt:
    print("\nExiting. Cleaning up...")
    GPIO.cleanup()
