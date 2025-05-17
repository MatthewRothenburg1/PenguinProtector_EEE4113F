from picamera2 import Picamera2
import RPi.GPIO as GPIO
import requests
import io
import time
import cv2
import threading

# === Configuration ===
PIR_PIN = 22
SERVER_URL = "http://192.168.3.146:8080"  # Local testing server
# SERVER_URL = "https://flask-fire-837838013707.africa-south1.run.app"  # For deployment

debounce_seconds = 10
camera_lock = threading.Lock()
listening = True

# === Deterrent Stub ===
def deterrent():
    print("Deterrent triggered!")

# === Upload Image ===
def upload_image(image_bytes_io):
    response = requests.post(
        f"{SERVER_URL}/upload_to_vision",
        files={"file": ("photo.jpg", image_bytes_io.getvalue(), "image/jpeg")}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print("Image upload failed:", response.text)
        return None


# === Upload Video ===
def upload_video(path, ID, triggered):
    with open(path, 'rb') as f:
        response = requests.post(
            f"{SERVER_URL}/upload_video",
            data={"ID": ID, "deterrent": triggered},
            files={"file": f}
        )
    if response.status_code == 200:
        print("Video uploaded successfully:", response.json())
    else:
        print("Video upload failed:", response.text)

# === Motion Event Handler ===
def motion_detected(channel):
    global listening
    if not listening:
        return
    listening = False
    threading.Thread(target=handle_motion).start()

def handle_motion():
    global listening
    print("Motion detected. Initializing camera...")

    with camera_lock:
        picam2 = Picamera2()
        picam2.start()
        time.sleep(2)  # Warm-up

        # Capture photo
        image_path = "/tmp/capture.jpg"
        picam2.capture_file(image_path)

        # Record 10-second video
        video_path = "/tmp/motion_video.h264"
        picam2.start_recording(video_path)
        time.sleep(10)
        picam2.stop_recording()
        picam2.close()

    # Upload image
    result = upload_image(image_path)

    if result and "ID" in result:
        response_id = result["ID"]
        print(f"Image uploaded with ID: {response_id}")

        if result.get("detected") == True:
            deterrent()
            triggered = "true"
        else:
            print("No animal detected. Starting 10 second cooldown...")
            triggered = "false"
            time.sleep(debounce_seconds)

        # Upload video
        upload_video(video_path, response_id, triggered)

    else:
        print("Skipping video upload due to failed image upload.")

    listening = True

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=motion_detected, bouncetime=200)

print("System ready. Waiting for motion...")

# === Keep running until Ctrl+C ===
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting. Cleaning up...")
    GPIO.cleanup()
