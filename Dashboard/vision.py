import cv2
import time
import requests

SERVER_URL = "https://flask-fire-837838013707.africa-south1.run.app"  # Your API server

def upload_image_from_memory(image_bytes):
    files = {"file": ("frame.jpg", image_bytes, "image/jpeg")}
    try:
        response = requests.post(f"{SERVER_URL}/upload_to_stream", files=files)
        if response.status_code == 200:
            return response.json()
        else:
            print("Image upload failed:", response.text)
            return None
    except requests.exceptions.RequestException as e:
        print("Request error:", e)
        return None

def capture_and_upload_stream():
    cap = cv2.VideoCapture(0)
    time.sleep(0.5)  # Allow camera to warm up

    if not cap.isOpened():
        print("Failed to open camera.")
        return

    print("Starting high-speed image stream upload...")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Encode frame to JPEG in memory
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                continue

            image_bytes = buffer.tobytes()
            upload_image_from_memory(image_bytes)
    except KeyboardInterrupt:
        print("Stream stopped by user.")
    finally:
        cap.release()

if __name__ == "__main__":
    capture_and_upload_stream()
