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
VIDEO_DURATION = random.randint(50, 59)  # 50–59 sec
FONT_PATH = "NotoSans-Devanagari.ttf"
BGM_PATH = "background_music.mp3"  # background music in repo
DOUBLE_IMAGE_TIME = True  # True to double image display time

# -----------------------------
# Topics
# -----------------------------
with open("topics.txt", "r", encoding="utf-8") as f:
    all_topics = [line.strip() for line in f if line.strip()]

used_topics = set()
if os.path.exists("used.txt"):
    with open("used.txt", "r", encoding="utf-8") as f:
        used_topics = set(line.strip() for line in f if line.strip())

available_topics = [t for t in all_topics if t not in used_topics]
if not available_topics:
    used_topics.clear()
    available_topics = all_topics.copy()

topic = random.choice(available_topics)
with open("used.txt", "a", encoding="utf-8") as f:
    f.write(topic + "\n")

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
    images = []
    try:
        if not GOOGLE_KEY or not GOOGLE_CX:
            return []

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query, "cx": GOOGLE_CX, "key": GOOGLE_KEY,
            "searchType": "image", "num": num, "imgSize": "large", "safe": "high"
        }

        r = requests.get(url, params=params)
        data = r.json()
        if "items" not in data:
            return []

        for idx, item in enumerate(data["items"]):
            link = item.get("link")
            if not link: continue
            try:
                img = requests.get(link, timeout=10)
                fname = f"images/google_{idx}.jpg"
                with open(fname, "wb") as f:
                    f.write(img.content)
                if os.path.getsize(fname) > 1024:
                    images.append(fname)
            except:
                continue
    except:
        pass
    return images

def fetch_pexels_images(query, num=10):
    images = []
    try:
        if not PEXELS_KEY:
            return []
        headers = {"Authorization": PEXELS_KEY}
        url = "https://api.pexels.com/v1/search"
        params = {"query": query, "per_page": num}
        r = requests.get(url, headers=headers, params=params)
        data = r.json()
        for idx, photo in enumerate(data.get("photos", [])):
            link = photo["src"]["large"]
            try:
                img = requests.get(link, timeout=10)
                fname = f"images/pexels_{idx}.jpg"
                with open(fname, "wb") as f:
                    f.write(img.content)
                if os.path.getsize(fname) > 1024:
                    images.append(fname)
            except:
                continue
    except:
        pass
    return images

def get_images(query, num=10):
    images = fetch_google_images(query, num)
    if len(images) < num:
        images += fetch_pexels_images(query, num - len(images))
    if len(images) < 5:
        raise Exception(f"❌ Not enough images for {query}")
    return images

images = get_images(topic, num=10)

# -----------------------------
# Helper: crop to fill frame
# -----------------------------
def crop_to_frame(img, width, height):
    im_w, im_h = img.size
    aspect_target = width / height
    aspect_img = im_w / im_h

    if aspect_img > aspect_target:
        new_w = int(im_h * aspect_target)
        left = (im_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, im_h))
    else:
        new_h = int(im_w / aspect_target)
        top = (im_h - new_h) // 2
        img = img.crop((0, top, im_w, top + new_h))
    return img.resize((width, height))

# -----------------------------
# Step 3: Create Video with zoom
# -----------------------------
print("🎬 Creating video with zoom effect...")
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))

font_size = 36
try:
    font = ImageFont.truetype(FONT_PATH, font_size)
except IOError:
    print(f"❌ Font not found: {FONT_PATH}")
    exit()

wrapped_lines = wrap(bio_text, width=30, break_long_words=False, replace_whitespace=False)
total_lines = len(wrapped_lines)
frames_total = VIDEO_DURATION * FPS
frames_per_line = max(1, frames_total // total_lines)
if DOUBLE_IMAGE_TIME:
    frames_per_line *= 2

for i, line in enumerate(wrapped_lines):
    img_file = images[i % len(images)]
    img_base = Image.open(img_file).convert("RGB")
    img_base = crop_to_frame(img_base, WIDTH, HEIGHT)

    for f in range(frames_per_line):
        # zoom effect: scale 1.0 -> 1.1 -> 1.0
        scale = 1.0 + 0.05 * np.sin(np.pi * f / frames_per_line)
        new_w, new_h = int(WIDTH * scale), int(HEIGHT * scale)
        img = img_base.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - WIDTH)//2
        top = (new_h - HEIGHT)//2
        img = img.crop((left, top, left+WIDTH, top+HEIGHT))

        draw = ImageDraw.Draw(img)
        bbox = font.getbbox(line)
        line_w, line_h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        pos = ((WIDTH-line_w)//2, HEIGHT-line_h-50)
        # shadow
        draw.text((pos[0]+2, pos[1]+2), line, font=font, fill=(0,0,0))
        draw.text(pos, line, font=font, fill=(255,255,255))

        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        video.write(frame)

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
# Step 5: Add Background Music
# -----------------------------
print("🎵 Adding background music...")
bgm = AudioSegment.from_file(BGM_PATH) - 12
voiceover = AudioSegment.from_file(AUDIO_FILENAME)
if len(bgm) < len(voiceover):
    bgm = bgm * (len(voiceover) // len(bgm) + 1)
bgm = bgm[:len(voiceover)]
final_audio = voiceover.overlay(bgm)
final_audio.export(AUDIO_FILENAME, format="mp3")
print("✅ Background music added!")

# -----------------------------
# Step 6: Merge Video + Audio
# -----------------------------
print("🔀 Merging video + audio...")
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)
print("✅ Final video ready!")

# -----------------------------
# Step 7: Upload to YouTube
# -----------------------------
print("📤 Uploading to YouTube...")
CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

creds = Credentials(None, refresh_token=REFRESH_TOKEN,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET)
creds.refresh(google.auth.transport.requests.Request())
youtube = build("youtube", "v3", credentials=creds)

safe_description = (
    f"Life of {topic} ❤️❤️❤️❤️"
    f"इस शॉर्ट वीडियो में आप {topic} के जीवन, संघर्ष और योगदान के बारे में जानेंगे।\n\n"
    "#Shorts #Motivation #History"
)

tags = [topic, "जीवनी", "Motivation", "Success", "Inspiration", "India", "History",
        "Biography", "Life Story", "Leadership", "Quotes", "Legacy",
        "Famous People", "Education", "Struggle", "Shorts", "Hindi", "ज्ञान", "Learning", "Wisdom"]

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
