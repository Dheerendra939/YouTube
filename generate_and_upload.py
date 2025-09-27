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
VIDEO_DURATION = random.randint(50, 59)  # 50–59 sec
FONT_PATH = "NotoSans-Devanagari.ttf"

# -----------------------------
# Topics for shorts
# -----------------------------
TOPICS = [
    "Mahatma Gandhi", "Swami Vivekananda", "APJ Abdul Kalam", "Bhagat Singh",
    "Rani Lakshmibai", "Chanakya", "Rabindranath Tagore", "Sardar Vallabhbhai Patel",
    "Subhas Chandra Bose", "Kalpana Chawla", "Albert Einstein", "Nikola Tesla",
    "Mother Teresa", "Martin Luther King Jr", "Steve Jobs", "Elon Musk"
]
topic = random.choice(TOPICS)
print(f"🎯 Selected topic: {topic}")

# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-flash")
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate Script
# -----------------------------
print(f"📖 Generating biography of {topic} in Hindi...")
bio_prompt = f"write a 55 second motivational biography of {topic} in Hindi. Keep it for narration only, no extra lines."
bio_resp = gemini_model.generate_content(bio_prompt)
bio_text = bio_resp.text.strip()
print("✅ Script generated!")

# -----------------------------
# -----------------------------
# Step 2: Fetch Images (Google first, fallback Pexels)
# -----------------------------
print("🖼️ Fetching images...")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
images = []
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

import imghdr

def download_and_validate(img_url, save_path):
    """Download image and validate it’s real (jpg/png)."""
    try:
        r = requests.get(img_url, timeout=10, stream=True)
        if r.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

            # Validate image format
            if imghdr.what(save_path) in ["jpeg", "png", "jpg"]:
                return True
            else:
                print(f"⚠️ Skipping invalid file (not an image): {img_url}")
                os.remove(save_path)
                return False
        else:
            print(f"⚠️ Failed to fetch {img_url} ({r.status_code})")
            return False
    except Exception as e:
        print(f"⚠️ Error downloading {img_url}: {e}")
        return False


# --- Try Google Custom Search ---
try:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    GOOGLE_CX = os.environ.get("GOOGLE_CX")

    if GOOGLE_API_KEY and GOOGLE_CX:
        print("🔎 Fetching from Google Images...")
        google_url = (
            f"https://www.googleapis.com/customsearch/v1?q={topic}"
            f"&cx={GOOGLE_CX}&searchType=image&num=15&key={GOOGLE_API_KEY}"
        )
        r = requests.get(google_url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for i, item in enumerate(data.get("items", [])):
                img_url = item["link"]
                img_path = os.path.join(image_folder, f"google_{i}.jpg")
                if download_and_validate(img_url, img_path):
                    images.append(img_path)
                    print(f"✅ Google: {img_path}")
        else:
            print(f"❌ Google Images API error: {r.text}")
    else:
        print("⚠️ Google API key or CX not set. Skipping Google fetch.")
except Exception as e:
    print(f"❌ Google fetch failed: {e}")


# --- Fallback: Pexels if <10 valid images ---
if len(images) < 10:
    print("📸 Falling back to Pexels...")
    headers = {"Authorization": PEXELS_API_KEY}
    pexels_url = "https://api.pexels.com/v1/search"
    try:
        r = requests.get(pexels_url, headers=headers, params={"query": topic, "per_page": 15}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for i, photo in enumerate(data.get("photos", [])):
                img_url = photo["src"]["large"]
                img_path = os.path.join(image_folder, f"pexels_{i}.jpg")
                if download_and_validate(img_url, img_path):
                    images.append(img_path)
                    print(f"✅ Pexels: {img_path}")
        else:
            print(f"❌ Pexels API error: {r.text}")
    except Exception as e:
        print(f"❌ Pexels fetch failed: {e}")

# --- Final Check ---
if len(images) < 10:
    raise Exception("❌ Not enough valid images. Need at least 10.")

print(f"✅ Got {len(images)} valid images")
# -----------------------------
# Step 3: Create Video
# -----------------------------
print("🎬 Creating video...")
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))

font_size = 36
try:
    font = ImageFont.truetype(FONT_PATH, font_size)
except IOError:
    print(f"❌ Font not found: {FONT_PATH}")
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
    pos = ((WIDTH - line_w) // 2, HEIGHT - 200)
    draw.text(pos, line, font=font, fill=(255, 255, 255))

    overlay_cv2 = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for _ in range(frames_per_line):
        video.write(overlay_cv2)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Generate TTS
# -----------------------------
print("🎙️ Generating Hindi voiceover...")
tts_json = os.environ["TTS"]
credentials_info = json.loads(tts_json)
credentials = service_account.Credentials.from_service_account_info(credentials_info)
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, pitch=-6)

response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
with open(AUDIO_FILENAME, "wb") as f:
    f.write(response.audio_content)
print("✅ Voiceover ready!")

# -----------------------------
# Step 5: Merge Video + Audio
# -----------------------------
print("🔀 Merging video + audio...")
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

safe_description = (
    f"{topic} की प्रेरणादायक 55 सेकंड जीवनी। "
    f"इस शॉर्ट वीडियो में आप {topic} के जीवन, संघर्ष और योगदान के बारे में जानेंगे।\n\n"
    "#Shorts #Motivation #History"
)

tags = [
    topic, "जीवनी", "Motivation", "Success", "Inspiration", "India", "History",
    "Biography", "Life Story", "Leadership", "Quotes", "Legacy",
    "Famous People", "Education", "Struggle", "Shorts", "Hindi", "ज्ञान", "Learning", "Wisdom"
]

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": f"{topic} की 55 सेकंड प्रेरणादायक जीवनी #Shorts",
            "description": safe_description[:4500],
            "tags": tags,
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=FINAL_FILENAME
)

response = request.execute()
print(f"✅ Upload complete! Video: https://www.youtube.com/watch?v={response['id']}")
