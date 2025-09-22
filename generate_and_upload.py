import os
import cv2
import numpy as np
from gtts import gTTS
import subprocess
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280   # Vertical 9:16
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
TEXT = "This is a 10 second test short video generated automatically!"
DURATION = 10

# -----------------------------
# Step 1: Generate video with text
# -----------------------------
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.2
thickness = 2
color = (255, 255, 255)

(text_w, text_h), _ = cv2.getTextSize(TEXT, font, font_scale, thickness)
pos = (WIDTH // 2 - text_w // 2, HEIGHT // 2)

frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
cv2.putText(frame, TEXT, pos, font, font_scale, color, thickness, cv2.LINE_AA)

for _ in range(DURATION * FPS):
    video.write(frame)

video.release()

# -----------------------------
# Step 2: Generate TTS audio
# -----------------------------
tts = gTTS(TEXT)
tts.save(AUDIO_FILENAME)

# -----------------------------
# Step 3: Merge video + audio
# -----------------------------
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)

# -----------------------------
# Step 4: Upload to YouTube
# -----------------------------
CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
creds.refresh(google.auth.transport.requests.Request())
youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Test Auto Short #Shorts",
            "description": "This is a test short generated automatically. #Shorts",
            "tags": ["Shorts", "Automation", "YouTube API"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    },
    media_body=FINAL_FILENAME
)
response = request.execute()

print(f"✅ Uploaded as Short! Video ID: {response['id']}")
