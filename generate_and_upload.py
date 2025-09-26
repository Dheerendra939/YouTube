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
# Step 2: Image Fetch (Google → Pexels)
# -----------------------------
def fetch_google_images(query, num=15):
    GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
    GOOGLE_CX = os.environ.get("GOOGLE_CX")
    if not GEMINI_API_KEY or not GOOGLE_CX:
        print("⚠️ Google API key or CX not found.")
        return []
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"q": query, "cx": GOOGLE_CX, "key": GEMINI_API_KEY, "searchType": "image", "num": num}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return [item["link"] for item in data.get("items", [])]
        else:
            print("❌ Google Images API error:", r.text)
            return []
    except Exception as e:
        print("❌ Google fetch failed:", e)
        return []

def fetch_images(query, min_required=10):
    image_folder = "images"
    os.makedirs(image_folder, exist_ok=True)
    images = []

    # Google first
    print("🔎 Fetching from Google Images...")
    google_links = fetch_google_images(query, num=15)
    for i, url in enumerate(google_links):
        try:
            img_path = os.path.join(image_folder, f"google_{i}.jpg")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(r.content)
                images.append(img_path)
        except:
            pass

    # Pexels fallback
    if len(images) < min_required:
        print("📸 Falling back to Pexels...")
        PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
        if PEXELS_API_KEY:
            headers = {"Authorization": PEXELS_API_KEY}
            pexels_url = "https://api.pexels.com/v1/search"
            try:
                r = requests.get(pexels_url, headers=headers, params={"query": query, "per_page": 15}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for i, photo in enumerate(data.get("photos", [])):
                        img_url = photo["src"]["large"]
                        img_path = os.path.join(image_folder, f"pexels_{i}.jpg")
                        img_data = requests.get(img_url, timeout=10).content
                        with open(img_path, "wb") as f:
                            f.write(img_data)
                        images.append(img_path)
                else:
                    print(f"❌ Pexels API error: {r.text}")
            except Exception as e:
                print(f"❌ Pexels fetch failed: {e}")

    if len(images) < min_required:
        raise Exception("❌ Not enough images (need at least 10).")

    return images

print("🖼️ Fetching images...")
images = fetch_images(topic, min_required=10)
print(f"✅ Got {len(images)} images")

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
