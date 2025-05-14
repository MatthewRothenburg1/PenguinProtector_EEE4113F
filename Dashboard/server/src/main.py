#################################################################
#Author: Matthew Rothenburg
#Date:  19/04/2025
#Description: This is the main FastAPI application for the Penguin Protector system.
#It is a server application built to run on Google Cloud Run.
#It receives data from a ground camera in order to detect predator threats and 
#activate deterrents accordingly.
#It interacts with a Raspberry Pi client that passes through images that are sent to 
#Google's Cloud Vision API for analysis. The results are then sent to a Google Sheet for
#record keeping and sent to the client for display on a web page.
##################################################################
#This was designed for the EEE4113F course at the University of Cape Town.


#SERVER_URL = "https://flask-fire-837838013707.africa-south1.run.app/upload_frame"

from fastapi import FastAPI, UploadFile, File, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates # type: ignore
from fastapi.staticfiles import StaticFiles

from io import BytesIO
import time

from google.cloud import vision
from google.oauth2 import service_account # type: ignore
from googleapiclient.discovery import build # type: ignore
from googleapiclient.http import MediaIoBaseUpload # type: ignore
from mimetypes import guess_type
import requests
import firebase_admin
from firebase_admin import credentials, firestore, db
from telegram import Bot # type: ignore
# Create a FastAPI application instance
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

#Frame buffer for the latest image
latest_frame = BytesIO()
GOOGLE_CLOUD_PROJECT_ID = 'design-dashboard-eee4113f' # type: ignore

TELEGRAM_TOKEN = '7713440185:AAEeLw8dRbzNgN3hsFGvqnZVi_wkgR6f_tM'
bot = Bot(token = TELEGRAM_TOKEN)
CHAT_ID = '7941423246'
# Telegram API URL for sending a message
telegram_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'

###############################################################################################
# Google API Stuff
###############################################################################################

# Service account credentials
creds = service_account.Credentials.from_service_account_file(
    'design-dashboard-eee4113f-0fab4abb4b04.json',
    scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-platform']  # Correct scope for Drive access
)
creds2 = credentials.Certificate('design-dashboard-eee4113f-0fab4abb4b04.json')

firebase_admin.initialize_app(creds2, {
    'databaseURL': 'https://design-dashboard-eee4113f-default-rtdb.firebaseio.com'
})

# Now you can access the database

# Build Google API service clients
drive_service = build('drive', 'v3', credentials=creds)
sheets_service = build('sheets', 'v4', credentials=creds)
vision_client = vision.ImageAnnotatorClient(credentials=creds)





# Folder ID for Google Drive
PHOTOS_ID = '1mMD_hPlF4bP9lcVVpjf499byGWU52rS8'  # PenguinProtector/Photos
VIDEOS_ID = '14Si2Uevxrns5bMSnfFt_AJANKfkSgbMj'  # PenguinProtector/Videos

# Upload image to Google Drive
def upload_to_drive(file_stream, filename, mimetype):
    file_metadata = {
        'name': filename,
        'parents': [PHOTOS_ID]
    }
    media = MediaIoBaseUpload(file_stream, mimetype=mimetype)

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return uploaded_file.get('id')

# Upload video to Google Drive (Placeholder)
def upload_video_to_drive(file_stream, filename, mimetype):
    file_metadata = {
        'name': filename,
        'parents': [VIDEOS_ID]
    }
    media = MediaIoBaseUpload(file_stream, mimetype=mimetype)

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return uploaded_file.get('id')

def upload_image_to_vision(file_stream):
    
    # Read image content
    content = file_stream.read()
    image = vision.Image(content=content)

    response = vision_client.object_localization(image=image)
    # Access the localized_object_annotations properly using dot notation
    objects = response.localized_object_annotations

    return objects

def generate_from_memory():
    global latest_frame
    while True:
        if latest_frame.getbuffer().nbytes > 0:
            frame = latest_frame.getvalue()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )
        time.sleep(0.1)

def get_detection_state():
    ref = db.reference('/DetectionState')
    state = ref.get()
    if (state):
        ref.set(False)
        return True
    elif (not state):
        return False
    else:
        return
    
def get_streaming_state():
    ref = db.reference('/StreamingState')
    return ref.get()

def set_streaming_state(x):
    ref = db.reference('/StreamingState')
    ref.set(x)

def evaluate_vision_response(response):
    # Placeholder for evaluating the vision response
    # You can implement your logic here based on the response from Google Vision API
    for obj in response:
        # Check if the object is 'Person' and if the score is greater than 0.5
        if obj.name == 'Person' and obj.score > 0.5:
            return True
    # If no matching 'Person' with score > 0.5, return False
    return False

def on_detection(file_bytes: BytesIO):
    # Upload the image to Google Drive
    mimetype = 'image/jpeg'  # Adjust based on your image type
    upload_to_drive(file_bytes, 'detected_image.jpg', mimetype)
    # Send Telegram notification (Placeholder)
    send_photo_to_user(file_bytes, "Person detected!")
    return


def send_message_to_user(message):
    data = {
        'chat_id': CHAT_ID,
        'text': message
    }

    response = requests.post(telegram_url, data=data)

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message: {response.status_code}, {response.text}")

def send_photo_to_user(photo: BytesIO, caption: str = ''):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    photo.seek(0)
    files = {'photo': photo}
    data = {'chat_id': CHAT_ID, 'caption': caption}
    
    response = requests.post(url, files=files, data=data)
    
    if response.status_code == 200:
        print("Photo sent successfully!")
    else:
        print(f"Failed to send photo. Error: {response.text}")

# Upload data to Google Sheets (Placeholder)
def upload_data_to_sheets(data):
    return None


###############################################################################################
# FastAPI Routes
###############################################################################################

@app.get("/detection_state")
def get_detect():
    return get_detection_state()

@app.post("/upload_to_vision")
async def upload_to_vision(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    file_bytes = BytesIO(file.file.read())
    
    try:
        # Simulate uploading the image to Vision API
        response = upload_image_to_vision(file_bytes)
        
        # Evaluate the response to check for a detected person
        results = evaluate_vision_response(response)
        
        # If a person is detected, start the background task
        if results and background_tasks:
            background_tasks.add_task(on_detection, file_bytes)
        
        # Return the results of the detection check
        return {"person_detected": results}
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/get_streaming_state")
def get_detect():
    return get_streaming_state()

@app.post("/set_streaming_state")
def set_streaming_state_endpoint(value: bool = Query(...)):
    return set_streaming_state(value)


@app.post("/upload_to_stream")
async def upload_to_stream(file: UploadFile = File(...)):
    global latest_frame
    latest_frame = BytesIO(await file.read())
    latest_frame.seek(0)
    

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_from_memory(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

#API route to upload a received video to Google Drive
@app.post("/upload_video")
async def upload_video(file: UploadFile = File(...)):
    file_bytes = BytesIO(await file.read())
    mimetype = file.content_type or guess_type(file.filename)[0] or 'video/mp4'

    try:
        file_id = upload_video_to_drive(file_bytes, file.filename, mimetype)
        return JSONResponse(content={"message": "Video uploaded successfully", "file_id": file_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



###############################################################################################
# Run using: uvicorn main:app --host 0.0.0.0 --port 8080
###############################################################################################