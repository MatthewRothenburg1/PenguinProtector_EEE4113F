import cv2
import requests
from io import BytesIO
import time

# URL of the FastAPI endpoint
url = "http://localhost:8080/upload_to_vision"  # Adjust if needed
#url = "https://flask-fire-837838013707.africa-south1.run.app/upload_to_vision"  # Adjust if needed


# Set up the webcam capture
cap = cv2.VideoCapture(0)  # Use 0 for the default webcam

if not cap.isOpened():
    raise Exception("Could not open webcam")

# Function to capture and send an image from the webcam
def capture_and_upload():
    # Capture one frame from the webcam
    ret, frame = cap.read()
    
    if not ret:
        print("Failed to capture image")
        return

    # Encode the image as JPEG in memory (no need to save to disk)
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_bytes = img_encoded.tobytes()

    # Send the image to the FastAPI endpoint
    files = {"file": ("webcam_image.jpg", BytesIO(img_bytes), "image/jpeg")}
    try:
        response = requests.post(url, files=files)
        if response.status_code == 200:
            print("Image uploaded successfully.")
            print(response.json())  # Print any response from the server
        else:
            print(f"Failed to upload image: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error occurred while uploading image: {str(e)}")

# Continuously capture and upload images
capture_and_upload()

# Optionally, display the webcam feed


# Stop capturing when the user presses 'q'

# Release resources
cap.release()
cv2.destroyAllWindows()
