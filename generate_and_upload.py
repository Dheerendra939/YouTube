import os
import cv2
import numpy as np
import random
import subprocess
import requests
import google.generativeai as genai
from google.cloud import texttospeech
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.auth.transport.requests

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 55  # seconds
FONT_PATH = "NotoSans-Devanagari.ttf"  # Hindi font
MAX_IMAGES = 5

# -----------------------------
# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-pro")
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate Biography in Hindi
# -----------------------------
print("📖 Generating short Gandhi Ji biography in Hindi...")

bio_prompt = (
    "महात्मा गांधी की एक संक्षिप्त जीवनी लिखें जो 50 सेकंड के "
    "YouTube शॉर्ट्स के लिए उपयुक्त हो। सरल हिंदी भाषा का प्रयोग करें।"
)

bio_resp = gemini_model.generate_content(bio_prompt)

# Some responses are returned as list of candidates
bio_text = bio_resp.text.strip() if hasattr(bio_resp, "text") else str(bio_resp)
print("✅ Biography generated!")
# -----------------------------
# Step 2: Fetch Images
# -----------------------------
print("🖼️ Downloading images...")
image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/1e/Gandhi_seated.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/91/Gandhi_laughing.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/72/Gandhi_Spinning_Wheel.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/0/0e/Mahatma_Gandhi_1942.jpg"
]
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)
images = []

headers = {"User-Agent": "Mozilla/5.0"}
for i, url in enumerate(image_urls):
    img_path = os.path.join(image_folder, f"gandhi_{i}.jpg")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(r.content)
            images.append(img_path)
            print(f"✅ Downloaded: {img_path}")
        else:
            print(f"⚠️ Failed {url}, status code: {r.status_code}")
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")

# Ensure at least 5 images
if len(images) == 0:
    placeholder = "placeholder.jpg"  # Add a default image in repo
    images = [placeholder] * MAX_IMAGES
elif len(images) < MAX_IMAGES:
    while len(images) < MAX_IMAGES:
        images.append(random.choice(images))

# -----------------------------
# Step 3: Create Video with Hindi Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = (VIDEO_DURATION * FPS) // len(images)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

# Load font
try:
    font_size = 36
    font = ImageFont.truetype(FONT_PATH, font_size)
except IOError:
    print(f"❌ Could not find font {FONT_PATH}")
    exit()

# Wrap text
wrapped_lines = wrap(bio_text, width=30, break_long_words=False)

for img_file in images:
    img = Image.open(img_file).resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Vertical center
    total_text_height = len(wrapped_lines) * (font_size + 10)
    start_y = (HEIGHT - total_text_height) // 2

    for i, line in enumerate(wrapped_lines):
        line_w, line_h = draw.textsize(line, font=font)
        pos = ((WIDTH - line_w) // 2, start_y + i * (font_size + 10))
        draw.text(pos, line, font=font, fill=(255, 255, 255))

    overlay_cv2 = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for _ in range(frames_per_image):
        video.write(overlay_cv2)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Generate AI TTS in Hindi
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
tts_client = texttospeech.TextToSpeechClient()
synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    pitch=5
)
response = tts_client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)
with open(AUDIO_FILENAME, "wb") as f:
    f.write(response.audio_content)
print("✅ AI Hindi audio generated!")

# -----------------------------
# Step 5: Merge Video + Audio
# -----------------------------
print("🔀 Merging video and audio...")
try:
    subprocess.run([
        "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
        "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
    ], check=True)
    print("✅ Final video ready!")
except subprocess.CalledProcessError as e:
    print(f"❌ FFMPEG failed: {e}")
    exit()

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
print(f"✅ Upload complete! Video link: https://www.youtube.com/watch?v={response['id']}")
