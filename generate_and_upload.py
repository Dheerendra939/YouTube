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
import time

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
USED_TOPICS_FILE = os.path.join(os.environ.get("GITHUB_WORKSPACE", "."), "used_topics.json")

# -----------------------------
# Load used topics
# -----------------------------
if os.path.exists(USED_TOPICS_FILE):
    with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
        used_topics = json.load(f)
else:
    used_topics = []

# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-flash")
print("✅ Gemini AI ready!")

# -----------------------------
# Generate new topic
# -----------------------------
print("🎯 Generating new engaging topic...")
topic_prompt = (
    "Generate one highly engaging and motivational topic for a 55-second Hindi YouTube short "
    "about famous personalities, historical figures, scientists, or innovators. "
    "Avoid repeating topics from the following list:\n" + ", ".join(used_topics)
)
topic_resp = gemini_model.generate_content(topic_prompt)
topic = topic_resp.text.strip()
print(f"🆕 Selected topic: {topic}")

# Update used topics
used_topics.append(topic)
used_topics = used_topics[-1000:]  # keep last 1000 topics
with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
    json.dump(used_topics, f, ensure_ascii=False, indent=2)

# -----------------------------
# Step 1: Generate Script
# -----------------------------
print(f"📖 Generating 55 sec biography of {topic} in Hindi...")
bio_prompt = f"Write a 55-second motivational biography of {topic} in Hindi. Keep it concise for narration only, no extra lines."
bio_resp = gemini_model.generate_content(bio_prompt)
bio_text = bio_resp.text.strip()
print("✅ Script generated!")

# -----------------------------
# Step 2: Fetch Images
# -----------------------------
print("🖼️ Fetching images...")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
pexels_url = "https://api.pexels.com/v1/search"

headers = {"Authorization": PEXELS_API_KEY}
images = []
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

try:
    r = requests.get(pexels_url, headers=headers, params={"query": topic, "per_page": 15}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        for i, photo in enumerate(data.get("photos", [])):
            img_url = photo["src"]["large"]
            img_path = os.path.join(image_folder, f"pexels_{i}.jpg")
            img_data = requests.get(img_url, timeout=10).content
            with open(img_path, "wb") as f:
                f.write(img_data)
            images.append(img_path)
            print(f"✅ Pexels: {img_path}")
    else:
        print(f"❌ Pexels API error: {r.text}")
except Exception as e:
    print(f"❌ Pexels fetch failed: {e}")

# Fallback: Wikipedia
if len(images) < 10:
    print("⚠️ Not enough images, using Wikipedia fallback...")
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
                print(f"✅ Wiki: {img_path}")
        except:
            pass

if len(images) < 10:
    raise Exception("❌ No images available. Need at least 10.")

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
