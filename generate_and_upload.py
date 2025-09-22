# generate_and_upload.py

import cv2
import numpy as np
from gtts import gTTS
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os

# ----------------------------
# YouTube API Credentials
# ----------------------------
ACCESS_TOKEN = os.getenv("YOUTUBE_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")
CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")

# ----------------------------
# Video settings
# ----------------------------
VIDEO_FILENAME = "short_video.mp4"
AUDIO_FILENAME = "audio.mp3"
WIDTH, HEIGHT = 720, 480
FPS = 24
DURATION = 10  # seconds

TEXT = "Hello! This is a test Short from GitHub Actions."  # Text to display

# ----------------------------
# Step 1: Generate audio
# ----------------------------
tts = gTTS(TEXT)
tts.save(AUDIO_FILENAME)

# ----------------------------
# Step 2: Generate video frames
# ----------------------------
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

for i in range(FPS * DURATION):
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    # Background color
    frame[:] = (50, 50, 200)
    
    # Put text in the center
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (255, 255, 255)
    thickness = 2
    text_size = cv2.getTextSize(TEXT, font, font_scale, thickness)[0]
    text_x = (WIDTH - text_size[0]) // 2
    text_y = (HEIGHT + text_size[1]) // 2
    cv2.putText(frame, TEXT, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    video.write(frame)

video.release()

# ----------------------------
# Step 3: Combine audio + video using ffmpeg
# ----------------------------
import subprocess
final_video = "final_short.mp4"
subprocess.run([
    "ffmpeg", "-y",
    "-i", VIDEO_FILENAME,
    "-i", AUDIO_FILENAME,
    "-c:v", "copy",
    "-c:a", "aac",
    "-shortest",
    final_video
])

# ----------------------------
# Step 4: Upload to YouTube
# ----------------------------
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
creds = Credentials(
    token=ACCESS_TOKEN,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Test Short from GitHub Actions",
            "description": "This is a test Short uploaded automatically via GitHub Actions.",
            "tags": ["test", "github actions", "youtube short"],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "private"
        }
    },
    media_body=final_video
)

response = request.execute()
print("✅ Video uploaded successfully! Video ID:", response["id"])
