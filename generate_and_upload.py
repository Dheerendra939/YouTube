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
import imghdr
import traceback

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
FONT_PATH = "NotoSans-Devanagari.ttf"
VIDEO_DURATION = random.randint(50, 59)  # 50–59 sec

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
            print("❌ Missing GOOGLE_API_KEY or GOOGLE_CX in environment variables")
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
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if "error" in data:
            print("❌ Google API Error:", data["error"].get("message", "Unknown error"))
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
                print(f"⚠️ Failed to fetch {link}: {e}")
    except Exception as e:
        print("❌ Exception in Google fetch:", e)
        traceback.print_exc()
    return images

def fetch_pexels_images(query, num=10):
    print("📸 Fetching from Pexels...")
    images = []
    try:
        if not PEXELS_KEY:
            print("❌ Missing PEXELS_API_KEY in environment variables")
            return []
        headers = {"Authorization": PEXELS_KEY}
        url = "https://api.pexels.com/v1/search"
        params = {"query": query, "per_page": num}
        r = requests.get(url, headers=headers, params=params, timeout=10)
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
                print(f"⚠️ Failed to fetch {link}: {e}")
    except Exception as e:
        print("❌ Exception in Pexels fetch:", e)
        traceback.print_exc()
    return images

def get_images(query, num=10):
    images = fetch_google_images(query, num)
    if len(images) < num:
        print(f"⚠️ Only got {len(images)} from Google, trying Pexels...")
        extra = fetch_pexels_images(query, num - len(images))
        images.extend(extra)
    if len(images) < 5:
        raise Exception(f"❌ Not enough images. Needed {num}, got {len(images)}")
    print(f"✅ Got {len(images)} valid images")
    return images

images = get_images(topic, 10)

# -----------------------------
# Step 3: Create Video (with cropped images)
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
    img_base = Image.open(img_file)
    # Crop to short aspect ratio without stretching
    img_base = img_base.resize((WIDTH, int(img_base.height * WIDTH / img_base.width)))
    top = (img_base.height - HEIGHT) // 2
    if top < 0:
        top = 0
    img_base = img_base.crop((0, top, WIDTH, top + HEIGHT))
    img = img_base.copy()
    draw = ImageDraw.Draw(img)

    # Draw text in white
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
# Step 5: Merge Video + TTS + Background Music
# -----------------------------
print("🔀 Adding background music...")
tts_audio = AudioSegment.from_file(AUDIO_FILENAME)
bg_music = AudioSegment.from_file("background.mp3")

# Trim or loop music to match narration
if len(bg_music) > len(tts_audio):
    bg_music = bg_music[:len(tts_audio)]
else:
    repeats = int(len(tts_audio) / len(bg_music)) + 1
    bg_music = bg_music * repeats
    bg_music = bg_music[:len(tts_audio)]

bg_music = bg_music - 10  # reduce volume by 10 dB
combined_audio = tts_audio.overlay(bg_music)
combined_audio.export("final_audio.mp3", format="mp3")

subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", "final_audio.mp3",
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)
print("✅ Final video with background music ready!")

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
    f"{topic} "
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
