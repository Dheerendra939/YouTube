import os
import cv2
import numpy as np
import requests
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

# Short Gandhi Biography (50s total, ~8–10s per line)
SENTENCES = [
    "Mahatma Gandhi was born on 2nd October 1869 in Porbandar, India.",
    "He studied law in London and later fought against racism in South Africa.",
    "Returning to India, Gandhi led the struggle for independence through non-violence.",
    "His Salt March in 1930 inspired millions to join the freedom movement.",
    "Known as Bapu, he believed in truth, peace, and simplicity.",
    "Gandhi's vision shaped India’s path to independence and inspired the world."
]

IMAGE_URLS = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/10/Gandhi_SouthAfrica.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/91/Gandhi1930.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/14/Gandhi_Salt_March.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/4/4e/Gandhi_young.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/9d/Gandhi_and_Charkha.jpg"
]

# -----------------------------
# Step 1: Download images
# -----------------------------
image_files = []
for i, url in enumerate(IMAGE_URLS):
    filename = f"img_{i}.jpg"
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)
    image_files.append(filename)

# -----------------------------
# Step 2: Generate TTS audio for full script
# -----------------------------
full_text = " ".join(SENTENCES)
tts = gTTS(full_text)
tts.save(AUDIO_FILENAME)

# -----------------------------
# Step 3: Create video from images + text
# -----------------------------
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2
color = (255, 255, 255)

# Approx 50s total → each sentence gets ~8s
seconds_per_sentence = 50 // len(SENTENCES)

for idx, (sentence, img_file) in enumerate(zip(SENTENCES, image_files)):
    img = cv2.imread(img_file)
    img = cv2.resize(img, (WIDTH, HEIGHT))

    # Add sentence text at bottom
    (text_w, text_h), _ = cv2.getTextSize(sentence, font, font_scale, thickness)
    pos = (WIDTH // 2 - text_w // 2, HEIGHT - 100)

    frame = img.copy()
    cv2.putText(frame, sentence, pos, font, font_scale, color, thickness, cv2.LINE_AA)

    for _ in range(seconds_per_sentence * FPS):
        video.write(frame)

video.release()

# -----------------------------
# Step 4: Merge video + narration
# -----------------------------
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)

# -----------------------------
# Step 5: Upload to YouTube Shorts
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
            "title": "Mahatma Gandhi Biography #Shorts",
            "description": "A 50-second biography of Mahatma Gandhi, Father of the Nation. #Shorts",
            "tags": ["Gandhi", "Biography", "India", "Shorts"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    },
    media_body=FINAL_FILENAME
)
response = request.execute()
print(f"✅ Uploaded Gandhi Biography Short! Video ID: {response['id']}")
