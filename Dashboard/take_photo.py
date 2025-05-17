from picamera2 import Picamera2
import requests
import io
import time
import cv2

# Configuration
url = "http://192.168.3.146:8080/upload_to_vision"
capture_interval = 5  # seconds

# Initialize and start camera once
picam2 = Picamera2()
picam2.start()
print("Camera initialized and running.")

try:
    while True:
        loop_start = time.time()
        
        # Capture image to numpy array
        image_array = picam2.capture_array()

        # Encode to JPEG in memory
        success, encoded_image = cv2.imencode('.jpg', image_array)
        if not success:
            raise RuntimeError("Image encoding failed")
        image_bytes = io.BytesIO(encoded_image.tobytes())

        # Upload to server
        files = {"file": ("photo.jpg", image_bytes.getvalue(), "image/jpeg")}
        upload_start = time.time()
        response = requests.post(url, files=files)
        upload_elapsed = time.time() - upload_start

        # Print timing and server response
        print(f"[{time.strftime('%H:%M:%S')}] Upload time: {upload_elapsed:.2f} sec")
        print("Server response:", response.json())

        # Wait until 30 seconds total (capture + upload + delay)
        elapsed_total = time.time() - loop_start
        sleep_time = max(0, capture_interval - elapsed_total)
        time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\nInterrupted. Closing camera.")
    picam2.close()

