import os
import cv2
import requests
import wikipedia
import subprocess
from google.cloud import texttospeech
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

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
# Step 0: Setup Google TTS
# -----------------------------
with open("tts_credentials.json", "w") as f:
    f.write(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts_credentials.json"
tts_client = texttospeech.TextToSpeechClient()

# -----------------------------
# Step 1: Fetch Biography Text (Hindi)
# -----------------------------
print("📖 Fetching Gandhi Ji biography from Hindi Wikipedia...")
wikipedia.set_lang("hi")
bio_text = wikipedia.summary("महात्मा गांधी", sentences=5)
print("✅ Biography fetched in Hindi!")

# -----------------------------
# Step 2: Download Images
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
headers = {"User-Agent": "Mozilla/5.0"}
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
# Step 3: Generate Video with Centered Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = BIO_DURATION * FPS // len(image_files)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Split bio text into lines (~25 characters per line)
lines = []
line = ""
for word in bio_text.split():
    if len(line + " " + word) < 25:
        line += " " + word
    else:
        lines.append(line.strip())
        line = word
if line:
    lines.append(line.strip())

for img_file in image_files:
    img = cv2.imread(img_file)
    if img is None:
        continue
    img = cv2.resize(img, (WIDTH, HEIGHT))
    overlay = img.copy()

    total_text_height = len(lines) * 40
    start_y = HEIGHT // 2 - total_text_height // 2
    for i, l in enumerate(lines):
        (text_w, text_h), _ = cv2.getTextSize(l, font, font_scale, thickness)
        pos = (WIDTH // 2 - text_w // 2, start_y + i * 40)
        cv2.putText(overlay, l, pos, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    for _ in range(frames_per_image):
        video.write(overlay)
video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Generate AI Voiceover (Hindi)
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
response = tts_client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)
with open(AUDIO_FILENAME, "wb") as out:
    out.write(response.audio_content)
print("✅ AI Hindi audio generated!")

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

safe_description = bio_text.replace("\n", " ").replace("\r", " ")[:4500]

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "महात्मा गांधी की 50 सेकंड जीवनी #Shorts",
            "description": safe_description + "\n\n#Shorts #MahatmaGandhi #History",
            "tags": ["महात्मा गांधी", "जीवनी", "Shorts", "इतिहास"],
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=FINAL_FILENAME
)
response = request.execute()
print(f"✅ Uploaded as Short! Video ID: {response['id']}")
