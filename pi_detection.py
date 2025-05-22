#!/usr/bin/env python3
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import RPi.GPIO as GPIO
import requests
import io
import time
import os
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
#SERVER_URL = "http://192.168.3.185:8080"  #Josh Local Server
SERVER_URL = "https://flask-fire-837838013707.africa-south1.run.app"  # For deployment



def compress_video(input_path, output_path):
    subprocess.run([
        "ffmpeg", "-y","-i", input_path,
        "-vcodec", "libx264", "-crf", "28",  # Adjust CRF for more compression
        "-preset", "fast",
        output_path], check=True)


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
    picam2.switch_mode(still_config)
    print("Taking photo...")
    # Capture photo
    try:
        frame = picam2.capture_array()
        print("Photo captured.")
    except Exception as e:
        print("Error capturing photo:", e)
        return None
    print("Photo taken.")
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
            return data
        else:
            return None
            print(f"Failed to get data. Status code: {response.status_code}")
    except requests.RequestException as e:
        return None
    

def setStreamState(server_url, state):
    """
    Sends a request to set the streaming state on the server.

    Args:
        server_url (str): Base URL of the server (e.g., http://192.168.1.100:5000).
        state (str): Desired state, typically "on" or "off".

    Returns:
        bool: True if the state was successfully set, False otherwise.
    """
    try:
        response = requests.post(f"{server_url}/set_streaming_state?value={state}")
        if response.status_code == 200:
            print(f"Streaming state set to '{state}'.")
            return True
        else:
            print(f"Failed to set streaming state. Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        print("Error:", e)
        return False


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
    global triggered, picam2
    print("2")
    try:
        clear_Oled()
        textToOled("Motion Detected")
        print("3")
        frame = take_photo()
        if frame is None:
            return

        print("4")
        result = upload_image(frame)
        print("5")
        if result and "ID" in result:
            print("6")
            response_id = result["ID"]
            print(f"Image uploaded with ID: {response_id}")
            print(result)
            if result.get("detection") == True:
                picam2.switch_mode(video_config)
                triggered = "true"
                deterrent()
                clear_Oled()
                textToOled("Animal Detected")

                video_path = "/tmp/motion_video.h264"
                mp4_path = "/tmp/motion_video.mp4"

                encoder = H264Encoder()
                output = FileOutput(video_path)
                try:
                    picam2.start_recording(encoder, output)
                    clear_Oled()
                    textToOled("Taking Video")
                    time.sleep(5)
                    picam2.stop_recording()
                except Exception as e:
                    print("Camera recording error:", e)
                    return

                try:
                    subprocess.run(["MP4Box", "-add", video_path, mp4_path], check=True)
                except subprocess.CalledProcessError as e:
                    print("MP4Box failed:", e)
                    return

                mp4_compressed_path = "/tmp/motion_video_compressed.mp4"
                compress_video(mp4_path, mp4_compressed_path)

                if os.path.exists(mp4_compressed_path):
                    upload_video(mp4_compressed_path, response_id, triggered)
                else:
                    print("Video not found after conversion.")

            else:
                print("No animal detected. Skipping video. Starting cooldown...")
                triggered = "false"
        else:
            print("Skipping video upload due to failed image upload.")
    except Exception as e:
        print("Error in on_PIR:", e)
        return
    finally:
        time.sleep(2)

def get_IR_state():
    global IR_STATE
    try:
        ir_response = requests.get(f"{SERVER_URL}/get_ir_state")
        if ir_response.status_code == 200:
            IR_STATE = ir_response.json().get("ir_state", False)
            print(f"Updated IR_STATE: {IR_STATE}")
        else:
            print(f"Failed to get IR state. Status code: {ir_response.status_code}")
    except requests.RequestException as e:
        print("Error fetching IR state:", e)


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
still_config = picam2.create_still_configuration()
video_config = picam2.create_video_configuration()
picam2.configure(still_config)
picam2.start()
time.sleep(1)  # Warm-up
textToOled("Camera Initialised")
oled_screen.clear()
time.sleep(0.5)

prev_time_stream = 0
dots = 0
while(GPIO.input(BUTTON_PIN) == GPIO.HIGH):
    clear_Oled()
    network_info = get_network_info()
    textToOled(network_info + "."*dots + "\nPress Button to Arm")
    dots = (dots + 1) % 4  # Cycle from 0 to 3

    print(network_info)
    time.sleep(0.5)

textToOled("Starting Detction")
time.sleep(0.5)

for i in range(10):
    clear_Oled()
    textToOled("Arming in " + str(10-i))
    time.sleep(1)

IR_STATE = False
prev_time_ir_check = 0 
prev_detection_time = 0
IR_CHECK_INTERVAL = 5  # 30 minutes in seconds

try:
    while True:

        current_time = time.time()
        clear_Oled()
        textToOled("ARMED\n" + dots*".")
        dots = (dots + 1) % 10  # Cycle from 0 to 3
        if(current_time - prev_detection_time > 60):
            if(GPIO.input(PIR_PIN) == GPIO.HIGH):
                print("1")
                on_PIR()
                print("done")
                prev_detection_time = current_time
        # Check if it's time to update the IR state
        if current_time - prev_time_ir_check > IR_CHECK_INTERVAL:
            get_IR_state()
            prev_time_ir_check = current_time

        
        if(current_time - prev_time_stream > 5):
            stream_state = fetchStreamState()
            print(stream_state)
            if stream_state is True:
                STREAM_START_TIME = current_time
            dots = 0
            while(stream_state):
                clear_Oled()
                textToOled("Streaming" + dots*".")
                dots = (dots + 1) % 3
                current_time = time.time()
                stream_state = fetchStreamState()
                if(current_time - STREAM_START_TIME > 40):
                    clear_Oled()
                    setStreamState(SERVER_URL,False)
                frame = take_photo()
                uploadToStream(frame)
            prev_time_stream = current_time
            time.sleep(0.1)
        time.sleep(1)


            
except KeyboardInterrupt:
    print("\nExiting. Cleaning up...")
    GPIO.cleanup()
