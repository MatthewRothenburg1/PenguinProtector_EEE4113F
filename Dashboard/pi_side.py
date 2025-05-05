import cv2
import requests
import time

#Testing to see changes save message me if you see this @Matt

#with open("Venice_10.mp4", "rb") as f:
#    response = requests.post("http://localhost:8080/upload_video", files={"file": f})
#    print(response.json())
#sdskgjhsdgkhdsg

#SERVER_URL = "https://flask-fire-837838013707.africa-south1.run.app/upload_frame"
SERVER_URL = "http://localhost:8080/upload_frame"

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    _, jpeg = cv2.imencode('.jpg', frame)
    response = requests.post(
        SERVER_URL,
        files={"file": ("frame.jpg", jpeg.tobytes(), "image/jpeg")}
    )

    time.sleep(5)  # adjust frame rate here
