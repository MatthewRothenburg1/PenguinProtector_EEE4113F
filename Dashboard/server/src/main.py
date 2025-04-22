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

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from io import BytesIO
import time

from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from mimetypes import guess_type

# Create a FastAPI application instance
app = FastAPI()
templates = Jinja2Templates(directory="templates")

#Frame buffer for the latest image
latest_frame = BytesIO()


###############################################################################################
# Google API Stuff
###############################################################################################

# Service account credentials
creds = service_account.Credentials.from_service_account_file(
    'design-dashboard-eee4113f-0fab4abb4b04.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

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
    # Reset stream position to the beginning
    file_stream.seek(0)
    
    # Read image content
    content = file_stream.read()
    image = vision.Image(content=content)

    response = vision_client.object_localization(image=image)
    objects = response.localized_object_annotations

    # Parse and return the results
    results = []
    results.append({
            "description": objects[0].name,
            "score": objects[0].score
        })

    return results


# Upload data to Google Sheets (Placeholder)
def upload_data_to_sheets(data):
    return None


###############################################################################################
# FastAPI Routes
###############################################################################################

@app.post("/upload_frame")
async def upload_frame(file: UploadFile = File(...)):
    global latest_frame
    latest_frame = BytesIO(await file.read())
    latest_frame.seek(0)
    print(upload_image_to_vision(latest_frame))
    return {"message": "Frame received"}


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