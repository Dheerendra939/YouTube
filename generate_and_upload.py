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
from pydub import AudioSegment
import imghdr, traceback

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
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
# Step 2: Fetch Images
# -----------------------------
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")

os.makedirs("images", exist_ok=True)

def fetch_google_images(query, num=10):
    print("🔎 Fetching from Google Custom Search...")
    images = []
    try:
        if not GOOGLE_KEY or not GOOGLE_CX:
            print("❌ Missing GOOGLE_API_KEY or GOOGLE_CX")
            return []

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "cx": GOOGLE_CX,
            "key": GOOGLE_KEY,
            "searchType": "image",
            "num": num,
            "imgSize": "large",
            "safe": "high"
        }

        r = requests.get(url, params=params)
        data = r.json()

        if "error" in data:
            print("❌ Google API Error:", data["error"].get("message", "Unknown"))
            return []

        if "items" not in data:
            print("⚠️ Google returned no items:", data)
            return []

        for idx, item in enumerate(data["items"]):
            link = item.get("link")
            if not link:
                continue
            try:
                img = requests.get(link, timeout=10)
                fname = f"images/google_{idx}.jpg"
                with open(fname, "wb") as f:
                    f.write(img.content)
                if imghdr.what(fname):
                    print(f"✅ Google: {fname}")
                    images.append(fname)
                else:
                    print(f"⚠️ Invalid image skipped: {fname}")
            except Exception as e:
                print(f"⚠️ Failed {link}: {e}")
    except Exception as e:
        print("❌ Exception in Google fetch:", e)
        traceback.print_exc()
    return images

def fetch_pexels_images(query, num=10):
    print("📸 Fetching from Pexels...")
    images = []
    try:
        if not PEXELS_KEY:
            print("❌ Missing PEXELS_API_KEY")
            return []
        headers = {"Authorization": PEXELS_KEY}
        url = "https://api.pexels.com/v1/search"
        params = {"query": query, "per_page": num}

        r = requests.get(url, headers=headers, params=params)
        data = r.json()

        if "photos" not in data:
            print("⚠️ Pexels returned no photos:", data)
            return []

        for idx, photo in enumerate(data["photos"]):
            link = photo["src"]["large"]
            try:
                img = requests.get(link, timeout=10)
                fname = f"images/pexels_{idx}.jpg"
                with open(fname, "wb") as f:
                    f.write(img.content)
                if imghdr.what(fname):
                    print(f"✅ Pexels: {fname}")
                    images.append(fname)
                else:
                    print(f"⚠️ Invalid image skipped: {fname}")
            except Exception as e:
                print(f"⚠️ Failed {link}: {e}")
    except Exception as e:
        print("❌ Exception in Pexels fetch:", e)
        traceback.print_exc()
    return images

def get_images(query, num=10):
    images = fetch_google_images(query, num)
    if len(images) < num:
        print(f"⚠️ Only {len(images)} from Google, trying Pexels...")
        extra = fetch_pexels_images(query, num - len(images))
        images.extend(extra)
    if len(images) < 5:
        raise Exception(f"❌ Not enough images. Needed {num}, got {len(images)}")
    print(f"✅ Got {len(images)} valid images")
    return images

images = get_images(topic, 10)

# -----------------------------
# Step 3: Create Video (crop + sync with narration)
# -----------------------------
def resize_and_crop(img, target_width, target_height):
    aspect_ratio = img.width / img.height
    target_ratio = target_width / target_height
    if aspect_ratio > target_ratio:
        new_height = target_height
        new_width = int(aspect_ratio * new_height)
    else:
        new_width = target_width
        new_height = int(new_width / aspect_ratio)
    img = img.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    return img.crop((left, top, right, bottom))

print("🎬 Creating video...")

# Generate TTS early to sync video
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

narration = AudioSegment.from_file(AUDIO_FILENAME)
audio_duration = narration.duration_seconds
frames_total = int(audio_duration * FPS)

video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))

try:
    font = ImageFont.truetype(FONT_PATH, 36)
except IOError:
    print(f"❌ Font not found: {FONT_PATH}")
    exit()

wrapped_lines = wrap(bio_text, width=30, break_long_words=False, replace_whitespace=False)
frames_per_line = max(1, frames_total // len(wrapped_lines))
print(f"✅ Sync: {audio_duration:.2f}s, frames per line: {frames_per_line}")

for i, line in enumerate(wrapped_lines):
    img_file = images[i % len(images)]
    img_base = resize_and_crop(Image.open(img_file), WIDTH, HEIGHT)
    img = img_base.copy()
    draw = ImageDraw.Draw(img)
    bbox = font.getbbox(line)
    line_w, line_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((WIDTH - line_w) // 2, HEIGHT - 200)
    draw.text(pos, line, font=font, fill=(255, 255, 255, 255))
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for _ in range(frames_per_line):
        video.write(frame)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Mix Background Music
# -----------------------------
print("🎵 Adding background music...")
bg = AudioSegment.from_file("background.mp3") - 15
bg = bg[:len(narration)]
final_audio = narration.overlay(bg)
final_audio.export(AUDIO_FILENAME, format="mp3")
print("✅ Background music added!")

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
    f"Life of {topic} ❤️❤️❤️❤️"
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
            "title": f"Life of {topic} ❤️❤️❤️❤️ #Shorts",
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
