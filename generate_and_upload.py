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

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
FONT_PATH = "NotoSans-Devanagari.ttf"
VIDEO_DURATION = random.randint(50, 59)  # 50-59 sec
BACKGROUND_MUSIC_PATH = "background_music.mp3"  # stored in repo

# -----------------------------
# Topics
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
        params = {"q": query, "cx": GOOGLE_CX, "key": GOOGLE_KEY,
                  "searchType": "image", "num": num, "imgSize": "large", "safe": "high"}

        r = requests.get(url, params=params)
        data = r.json()
        if "error" in data:
            print("❌ Google API Error:", data["error"].get("message", "Unknown"))
            return []
        if "items" not in data:
            print("⚠️ No items returned by Google:", data)
            return []

        for idx, item in enumerate(data["items"]):
            link = item.get("link")
            if not link: continue
            try:
                img = requests.get(link, timeout=10)
                fname = f"images/google_{idx}.jpg"
                with open(fname, "wb") as f: f.write(img.content)
                if Image.open(fname): images.append(fname); print(f"✅ Google: {fname}")
            except: continue
    except Exception as e: print("❌ Exception in Google fetch:", e)
    return images

def fetch_pexels_images(query, num=10):
    print("📸 Fetching from Pexels...")
    images = []
    try:
        if not PEXELS_KEY: return []
        headers = {"Authorization": PEXELS_KEY}
        r = requests.get("https://api.pexels.com/v1/search", headers=headers, params={"query": query, "per_page": num})
        data = r.json()
        for idx, photo in enumerate(data.get("photos", [])):
            link = photo["src"]["large"]
            try:
                img = requests.get(link, timeout=10)
                fname = f"images/pexels_{idx}.jpg"
                with open(fname, "wb") as f: f.write(img.content)
                if Image.open(fname): images.append(fname); print(f"✅ Pexels: {fname}")
            except: continue
    except Exception as e: print("❌ Exception in Pexels fetch:", e)
    return images

def get_images(query, num=10):
    images = fetch_google_images(query, num)
    if len(images) < num:
        print(f"⚠️ Only got {len(images)} from Google, trying Pexels...")
        images += fetch_pexels_images(query, num - len(images))
    if len(images) < 5: raise Exception(f"❌ Not enough images. Needed {num}, got {len(images)}")
    print(f"✅ Got {len(images)} valid images")
    return images

images = get_images(topic, num=10)

# -----------------------------
# Step 3: Create Video
# -----------------------------
print("🎬 Creating video...")
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
font_size = 36
font = ImageFont.truetype(FONT_PATH, font_size)
wrapped_lines = wrap(bio_text, width=30)
total_lines = len(wrapped_lines)
frames_per_line = (VIDEO_DURATION * FPS) // total_lines

for i, line in enumerate(wrapped_lines):
    img_file = images[i % len(images)]
    img_base = Image.open(img_file)
    # Crop to short aspect ratio
    img_base = img_base.resize((WIDTH, int(img_base.height * WIDTH / img_base.width)))
    top = max((img_base.height - HEIGHT) // 2, 0)
    img_base = img_base.crop((0, top, WIDTH, top + HEIGHT))
    if img_base.mode != "RGB": img_base = img_base.convert("RGB")
    img = img_base.copy()
    draw = ImageDraw.Draw(img)
    bbox = font.getbbox(line)
    line_w, line_h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pos = ((WIDTH-line_w)//2, HEIGHT-200)
    draw.text(pos, line, font=font, fill=(255,255,255))
    overlay_cv2 = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for _ in range(frames_per_line): video.write(overlay_cv2)
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
with open(AUDIO_FILENAME, "wb") as f: f.write(response.audio_content)
print("✅ Voiceover ready!")

# -----------------------------
# Step 4b: Add Background Music
# -----------------------------
print("🎵 Adding background music...")
voice_audio = AudioSegment.from_mp3(AUDIO_FILENAME)
bg_music = AudioSegment.from_mp3(BACKGROUND_MUSIC_PATH)[:len(voice_audio)]
combined_audio = voice_audio.overlay(bg_music)
combined_audio.export(AUDIO_FILENAME, format="mp3")
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

creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token",
                    client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
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
