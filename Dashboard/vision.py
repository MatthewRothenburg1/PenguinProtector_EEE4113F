import cv2
import requests
from io import BytesIO
import uuid
import time

# URL of the FastAPI endpoint
url = "http://localhost:8080"  # Adjust if needed
#url = "https://flask-fire-837838013707.africa-south1.run.app/upload_to_vision"  # Adjust if needed

# === Configuration ===
SERVER_URL = url
IMAGE_CAPTURE_PATH = "capture.jpg"
VIDEO_CAPTURE_PATH = "video.mp4"
DETERRENT_TYPE = "sound"  # Change as needed

# === Step 1: Capture Image ===
def capture_image(path):
    cap = cv2.VideoCapture(0)
    time.sleep(2)  # Let camera warm up
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(path, frame)
    cap.release()
    return ret

# === Step 2: Upload Image ===
def upload_image(path):
    with open(path, 'rb') as f:
        response = requests.post(
            f"{SERVER_URL}/upload_to_vision",
            files={"file": f}
        )
    if response.status_code == 200:
        return response.json()
    else:
        print("Image upload failed:", response.text)
        return None

# === Step 3: Record Video ===
def record_video(path, duration=5, fps=20):
    cap = cv2.VideoCapture(0)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))

    start_time = time.time()
    while (time.time() - start_time) < duration:
        ret, frame = cap.read()
        if ret:
            out.write(frame)
        else:
            break
    cap.release()
    out.release()

# === Step 4: Upload Video ===
def upload_video(path, ID, deterrent):
    with open(path, 'rb') as f:
        response = requests.post(
            f"{SERVER_URL}/upload_video",
            data={"ID": ID, "deterrent": deterrent},
            files={"file": f}
        )
    if response.status_code == 200:
        print("Video uploaded successfully:", response.json())
    else:
        print("Video upload failed:", response.text)

# === Main Flow ===
if __name__ == "__main__":
    print("Capturing image...")
    if capture_image(IMAGE_CAPTURE_PATH):
        print("Uploading image...")
        result = upload_image(IMAGE_CAPTURE_PATH)

        if result and result.get("detection"):
            ID = result.get("ID")
            print(f"Detection confirmed! ID: {ID}")
            print("Recording video...")
            record_video(VIDEO_CAPTURE_PATH)
            print("Uploading video...")
            upload_video(VIDEO_CAPTURE_PATH, ID, DETERRENT_TYPE)
        else:
            print("No detection or failed upload.")
    else:
        print("Image capture failed.")