import os
import cv2
import random
import subprocess
import requests
import numpy as np
import google.generativeai as genai
from google.cloud import texttospeech
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.auth.transport.requests
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
import json

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 55  # seconds
FONT_PATH = "NotoSans-Devanagari.ttf"  # Ensure this font exists

# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-flash")
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate Biography in Hindi
# -----------------------------
print("📖 Generating short Gandhi Ji biography in Hindi...")
bio_prompt = "write 50 second motivational biography of mahatma gandhi in hindi. we will use it for narration so don't write any extra line."
bio_resp = gemini_model.generate_content(bio_prompt)
bio_text = bio_resp.text.strip()
print("✅ Biography generated!")

# -----------------------------
# Step 2: Fetch Images (Pexels + Fallback Wikipedia)
# -----------------------------
print("🖼️ Fetching images...")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
pexels_url = "https://api.pexels.com/v1/search"
query = "Mahatma Gandhi"

headers = {"Authorization": PEXELS_API_KEY}
images = []
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

try:
    r = requests.get(pexels_url, headers=headers, params={"query": query, "per_page": 5}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        for i, photo in enumerate(data.get("photos", [])):
            img_url = photo["src"]["large"]
            img_path = os.path.join(image_folder, f"pexels_{i}.jpg")
            img_data = requests.get(img_url, timeout=10).content
            with open(img_path, "wb") as f:
                f.write(img_data)
            images.append(img_path)
            print(f"✅ Downloaded from Pexels: {img_path}")
    else:
        print(f"❌ Pexels API error: {r.text}")
except Exception as e:
    print(f"❌ Pexels fetch failed: {e}")

# Fallback: Wikipedia images
if len(images) < 5:
    print("⚠️ Not enough images from Pexels, using Wikipedia fallback...")
    fallback_urls = [
        "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/1e/Gandhi_seated.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/91/Gandhi_laughing.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/72/Gandhi_Spinning_Wheel.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/0/0e/Mahatma_Gandhi_1942.jpg"
    ]
    for i, url in enumerate(fallback_urls):
        img_path = os.path.join(image_folder, f"wiki_{i}.jpg")
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(r.content)
                images.append(img_path)
                print(f"✅ Downloaded fallback: {img_path}")
        except:
            pass

if len(images) == 0:
    raise Exception("❌ No images available. Check your Pexels API key and fallback URLs.")

# Ensure at least 5 images
while len(images) < 5:
    images.append(random.choice(images))

# -----------------------------
# Step 3: Create Video with Line-by-Line Text
# -----------------------------
print("🎬 Creating video...")
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))

font_size = 36
try:
    font = ImageFont.truetype(FONT_PATH, font_size)
except IOError:
    print(f"❌ Could not find font file at {FONT_PATH}")
    exit()

wrapped_lines = wrap(bio_text, width=30, break_long_words=False, replace_whitespace=False)
total_lines = len(wrapped_lines)
frames_per_line = (VIDEO_DURATION * FPS) // total_lines

for i, line in enumerate(wrapped_lines):
    img_file = images[i % len(images)]
    img_base = Image.open(img_file).resize((WIDTH, HEIGHT))
    img = img_base.copy()
    draw = ImageDraw.Draw(img)

    bbox = font.getbbox(line)
    line_w, line_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((WIDTH - line_w) // 2, HEIGHT // 2 - line_h // 2)
    draw.text(pos, line, font=font, fill=(255, 255, 255))

    overlay_cv2 = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for _ in range(frames_per_line):
        video.write(overlay_cv2)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Generate AI TTS in Hindi with higher pitch
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
tts_json = os.environ["TTS"]
credentials_info = json.loads(tts_json)
credentials = service_account.Credentials.from_service_account_info(credentials_info)
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    pitch=-5  # slightly higher pitch
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
print(f"✅ Upload complete! Video link: https://www.youtube.com/watch?v={response['id']}")
