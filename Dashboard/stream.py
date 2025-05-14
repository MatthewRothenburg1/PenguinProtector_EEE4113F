import cv2
import requests
import asyncio
from io import BytesIO
import time

# Step 1: Setup webcam capture
cap = cv2.VideoCapture(0)  # 0 is the default camera

if not cap.isOpened():
    raise Exception("Failed to access webcam")

# Step 2: Function to upload image asynchronously to FastAPI
async def upload_image(img_bytes):
    url = "https://flask-fire-837838013707.africa-south1.run.app/upload_to_stream"  # Change to your FastAPI URL
    files = {
        "file": ("webcam_frame", BytesIO(img_bytes), "image/jpeg")
    }
    response = await asyncio.to_thread(requests.post, url, files=files)
    print(f"Status: {response.status_code}, Response: {response.text}")

# Step 3: Continuous streaming loop with reduced JPEG quality (to speed up)
while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to capture frame")
        break

    # Convert the frame to JPEG with reduced quality for faster encoding (lower compression)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]  # Lower quality for faster encoding
    _, img_encoded = cv2.imencode('.jpg', frame, encode_param)
    img_bytes = img_encoded.tobytes()  # No need to store it as JPEG

    # Asynchronously upload the image
    asyncio.run(upload_image(img_bytes))

    # Display the image locally (optional)
    
    # Check for 'q' key to stop streaming
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Optional: Upload at a specific interval (e.g., every 100ms for 10 fps)

# Release resources and close the OpenCV window
cap.release()
cv2.destroyAllWindows()
