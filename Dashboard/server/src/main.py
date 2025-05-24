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

from fastapi import FastAPI, UploadFile, File, Request, Query, BackgroundTasks, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates # type: ignore
from fastapi.staticfiles import StaticFiles

from io import BytesIO
import asyncio
import time
import uuid

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
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

#ToDO
#5 - Count detections vs Non-detections within (day, week, month)
#6 - Set up streaming
#7 - RTC config
#8 - RTC db field




app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

#Frame buffer for the latest image
latest_frame = BytesIO()
frame_event = asyncio.Event()  # Used to signal new frame arrival

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
    scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/spreadsheets']  # Correct scope for Drive access
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
SPREADSHEET_ID = '1RDzJ9jUoakI7AXR_NkeoroyjYiuy4Nq-OaEe4I-Ouvs' #Spreadsheet ID for Google Sheets

# Upload image to Google Drive
def upload_to_drive(file_stream, filename):
    mimetype = 'image/jpeg'  #Format for upload

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

    file_id = uploaded_file.get('id') #Get the file ID of the uploaded file

    return f'https://drive.google.com/file/d/{file_id}/preview' #Return the link to the photo preview

# Upload video to Google Drive (Placeholder)
def upload_video_to_drive(file_stream, filename):
    mimetype = 'video/mp4'
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

    file_id = uploaded_file.get('id') #Get the file ID of the uploaded file

    return f'https://drive.google.com/file/d/{file_id}/preview' #Return the link to the video preview

def upload_image_to_vision(file_stream):
    
    # Read image content
    content = file_stream.read()
    image = vision.Image(content=content)

    response = vision_client.object_localization(image=image)
    # Access the localized_object_annotations properly using dot notation
    objects = response.localized_object_annotations

    return objects

def get_number_of_detections():
    RANGE = "Sheet1!B:C"  #Columns of Time and Detection State
    
    response = sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE
    ).execute()

    rows = response.get("values", [])

    # Get current time
    now = datetime.now()

    # Time periods
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)
    one_month_ago = now - timedelta(days=30)

    # Initialize counts
    counts = {
        "hour": {"true": 0, "false": 0},
        "day": {"true": 0, "false": 0},
        "week": {"true": 0, "false": 0},
        "month": {"true": 0, "false": 0},
    }

    # Loop through rows and classify
    for row in rows:
        if len(row) < 2:
            continue

        try:
            timestamp = datetime.fromisoformat(row[0])
        except ValueError:
            continue

        result = row[1].strip().lower()

        if timestamp >= one_month_ago:
            counts["month"][result] += 1
        if timestamp >= one_week_ago:
            counts["week"][result] += 1
        if timestamp >= one_day_ago:
            counts["day"][result] += 1
        if timestamp >= one_hour_ago:
            counts["hour"][result] += 1
    return counts

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
        if obj.name == 'Animal' and obj.score > 0.3:
            return True
        if obj.name == 'Cat' and obj.score > 0.3:
            return True
        
    # If no matching 'Person' with score > 0.5, return False
    return False

def on_detection(file_bytes: BytesIO, results, ID):
    
    if(results): 
        send_photo_to_user(file_bytes, "Honey Badger!!! Activating Penguin Protector. May need backup.") #If the detction state is true send a notification to the user over telegram.

    photo_drive_link =   upload_to_drive(file_bytes, ID +'.jpg') #Upload the image to Google Drive and store the link
    local_time = datetime.now(ZoneInfo("Africa/Johannesburg")).replace(microsecond=0)
    detection_time = local_time.isoformat()
    upload_time_and_ID_to_sheets(ID, detection_time, results, photo_drive_link) #Upload the time and ID to Google Sheets
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

# Upload data to Google Sheets
def upload_time_and_ID_to_sheets(ID, time_taken, results, photo_link):
    
    sheet_range = 'Sheet1!A:D'  # Sheet name and columns A to D
    
    # Prepare the data row to append
    # 'results' is a boolean — we store "Detection" or "No Detection"
    values = [
        [ID, time_taken, results, photo_link]
    ]
    
    body = {
        'values': values
    }

    try:
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range,
            valueInputOption='RAW',
            body=body
        ).execute()
    except Exception as e:
        print(f"Error uploading to Sheets: {e}")
    return

def upload_video_and_detterent_to_sheets(ID,  deterrent, video_link):
    try:
        # Fetch only column A to find the row number of the matching ID
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:A'
        ).execute()
        values = result.get('values', [])

        # Search for the ID in column A
        for i, row in enumerate(values):
            if row and row[0] == ID:
                row_number = i + 1  # Convert zero-based index to 1-based for Sheets
                update_range = f'Sheet1!E{row_number}:F{row_number}'
                body = {
                    'values': [[deterrent, video_link]]
                }
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=update_range,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                return
        print(f"ID '{ID}' not found in column A.")
    except Exception as e:
        print(f"Error updating Sheets: {e}")



###############################################################################################
# FastAPI Routes
###############################################################################################

@app.post("/upload_to_vision")
async def upload_to_vision(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    file_bytes = BytesIO(file.file.read())
    
    try:

        ID = str(uuid.uuid4()) #Generate a unique ID upload in order to match indivdual uploads.

        response = upload_image_to_vision(file_bytes) #Upload the captured image to Google Vision API and store the response
        
        results = evaluate_vision_response(response) #Evaluate the response to check validity (Results = True if honeybadger/leopard)

        background_tasks.add_task(on_detection, file_bytes, results, ID) #If a person is detected, start the background task (upload to Google Drive, send Telegram message, etc.)
        
        return {"detection": results, "ID": ID}  #Return the results and the ID of the upload to the Raspberry PI
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


#API route to upload a received video to Google Drive
@app.post("/upload_video")
async def upload_video(
    ID: str = Form(...),              # Form field for ID
    deterrent: str = Form(...),       # Form field for deterrent
    file: UploadFile = File(...)      # File field for video
):
    file_bytes = BytesIO(await file.read())

    try:
        file_id = upload_video_to_drive(file_bytes, ID + '.mp4')  # Upload the video to Google Drive
        upload_video_and_detterent_to_sheets(ID, deterrent, file_id)  # Upload the video link and deterrent to Google Sheets
        
        return JSONResponse(content={
            "message": "Video uploaded successfully",
            "file_id": file_id,
            "ID": ID,
            "deterrent": deterrent
        })
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/get_streaming_state")
def get_detect():
    return get_streaming_state()


@app.post("/set_streaming_state")
def set_streaming_state_endpoint(value: bool = Query(...)):
    return set_streaming_state(value)


@app.post("/upload_to_stream")
async def upload_frame(file: UploadFile = File(...)):
    global latest_frame, frame_event
    latest_frame = BytesIO(await file.read())
    frame_event.set()
    return {"status": "Frame received"}

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_from_memory(), media_type="multipart/x-mixed-replace; boundary=frame")


async def generate_from_memory():
    global latest_frame, frame_event
    while True:
        await frame_event.wait()
        frame_event.clear()
        if latest_frame.getbuffer().nbytes > 0:
            frame = latest_frame.getvalue()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Coordinates for sunrise-sunset API
LAT = -34.454189  # 34°27’15.08” S
LON = 20.399619   # 20°23’58.63” E

@app.get("/get_ir_state")
def should_ir_be_on():
    try:
        # 1. Get current UTC time
        now_utc = datetime.now(timezone.utc)

        # 2. Get sunrise and sunset from sunrise-sunset.org API
        response = requests.get(
            "https://api.sunrise-sunset.org/json",
            params={"lat": LAT, "lng": LON, "formatted": 0}
        )
        data = response.json()

        if data["status"] != "OK":
            return {"error": "Could not retrieve sunrise/sunset data"}

        sunrise = datetime.fromisoformat(data["results"]["sunrise"]).astimezone(timezone.utc)
        sunset = datetime.fromisoformat(data["results"]["sunset"]).astimezone(timezone.utc)

        # 3. Add buffer
        sunrise_buffer = sunrise - timedelta(minutes=30)
        sunset_buffer = sunset + timedelta(minutes=30)

        # 4. Decision logic
        ir_on = now_utc < sunrise_buffer or now_utc > sunset_buffer

        return {"ir_on": ir_on}

    except Exception as e:
        return {"error": str(e)}


@app.get("/detection_stats")
def detection_stats():
    try:
        counts = get_number_of_detections()
        return JSONResponse(content=counts)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

###############################################################################################
# Run using: uvicorn main:app --host 0.0.0.0 --port 8080
###############################################################################################