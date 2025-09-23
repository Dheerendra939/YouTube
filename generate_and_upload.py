import os
import cv2
import numpy as np
import requests
import wikipedia
from gtts import gTTS
import subprocess
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280   # Vertical 9:16 for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
BIO_DURATION = 50  # seconds

# -----------------------------
# Step 1: Fetch Biography Text
# -----------------------------
print("📖 Fetching Gandhi Ji biography from Wikipedia...")
bio_text = wikipedia.summary("Mahatma Gandhi", sentences=5)
print("✅ Biography fetched!")

# -----------------------------
# Step 2: Fetch Images
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/14/Mahatma-Gandhi%2C_studio%2C_1931.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/76/MKGandhi.jpg"
]

image_files = []
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for i, url in enumerate(image_urls):
    img_path = os.path.join(image_folder, f"gandhi_{i}.jpg")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(r.content)
            image_files.append(img_path)
            print(f"✅ Downloaded: {img_path}")
        else:
            print(f"⚠️ Failed to download {url}, status code: {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

if not image_files:
    raise RuntimeError("❌ No images available for video.")

# -----------------------------
# Step 3: Generate Video with Images + Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = BIO_DURATION * FPS // len(image_files)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

for img_file in image_files:
    img = cv2.imread(img_file)
    if img is None:
        print(f"⚠️ Skipping {img_file} (invalid image).")
        continue

    img = cv2.resize(img, (WIDTH, HEIGHT))

    # Overlay biography text at bottom
    overlay = img.copy()
    wrapped_text = bio_text[:100] + "..."  # keep short
    (text_w, text_h), _ = cv2.getTextSize(wrapped_text, font, font_scale, thickness)
    pos = (WIDTH // 2 - text_w // 2, HEIGHT - 50)
    cv2.putText(overlay, wrapped_text, pos, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    for _ in range(frames_per_image):
        video.write(overlay)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Generate TTS Audio
# -----------------------------
print("🎙️ Generating audio...")
tts = gTTS(bio_text, lang="en")
tts.save(AUDIO_FILENAME)
print("✅ Audio generated!")

# -----------------------------
# Step 5: Merge Video + Audio
# -----------------------------
print("🔀 Merging video and audio...")
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)
print("✅ Final video ready!")

# -----------------------------
# Step 6: Upload to YouTube
# -----------------------------
print("📤 Uploading to YouTube...")
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
            "title": "Mahatma Gandhi 50s Biography #Shorts",
            "description": bio_text + "\n\n#Shorts #MahatmaGandhi #History",
            "tags": ["Mahatma Gandhi", "Biography", "Shorts", "History"],
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
print("✅ Video created!")

# -----------------------------
# Step 4: Generate TTS Audio
# -----------------------------
print("🎙️ Generating audio...")
tts = gTTS(bio_text, lang="en")
tts.save(AUDIO_FILENAME)
print("✅ Audio generated!")

# -----------------------------
# Step 5: Merge Video + Audio
# -----------------------------
print("🔀 Merging video and audio...")
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)
print("✅ Final video ready!")

# -----------------------------
# Step 6: Upload to YouTube
# -----------------------------
print("📤 Uploading to YouTube...")
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
            "title": "Mahatma Gandhi 50s Biography #Shorts",
            "description": bio_text + "\n\n#Shorts #MahatmaGandhi #History",
            "tags": ["Mahatma Gandhi", "Biography", "Shorts", "History"],
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
