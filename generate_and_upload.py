import os
import cv2
import random
import subprocess
import requests
import numpy as np
import google.generativeai as genai
from google.cloud import texttospeech
from google.oauth2 import service_account
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
VIDEO_DURATION = 50  # seconds
FONT_PATH = "NotoSans-Devanagari.ttf"  # Make sure this font exists

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
print("📖 Generating Gandhi Ji biography in Hindi...")
bio_prompt = "महात्मा गांधी का 50 सेकंड का संक्षिप्त जीवन परिचय हिंदी में लिखिए।"
bio_resp = gemini_model.generate_content(bio_prompt)
bio_text = bio_resp.text.strip()
print("✅ Biography generated!")

# -----------------------------
# -----------------------------
# Step 2: Get 10 valid image URLs from Gemini AI
# -----------------------------
print("🖼️ Generating 10 valid image URLs via Gemini AI...")

valid_image_urls = []

while len(valid_image_urls) < 10:
    remaining = 10 - len(valid_image_urls)
    image_prompt = f"Provide {remaining} copyright-free public domain images of Mahatma Gandhi. Only direct image URLs, one per line."
    try:
        response = gemini_model.generate_content(image_prompt)
        candidate_urls = [url.strip() for url in response.text.split("\n") if url.strip()]
        
        # Validate each URL
        headers = {"User-Agent": "Mozilla/5.0"}
        for url in candidate_urls:
            if len(valid_image_urls) >= 10:
                break
            try:
                r = requests.head(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    valid_image_urls.append(url)
            except:
                continue
    except Exception as e:
        print(f"⚠️ Gemini AI error: {e}")

print(f"✅ {len(valid_image_urls)} valid image URLs obtained!")

# -----------------------------
# Step 3: Download Images
# -----------------------------
print("📥 Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)
images = []

headers = {"User-Agent": "Mozilla/5.0"}
for i, url in enumerate(image_urls[:10]):
    img_path = os.path.join(image_folder, f"gandhi_{i}.jpg")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(r.content)
            images.append(img_path)
            print(f"✅ Downloaded: {img_path}")
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")

# Repeat images if less than 10
while len(images) < 10:
    images.append(random.choice(images))

# -----------------------------
# Step 4: Create Video with Line-by-Line Text
# -----------------------------
print("🎬 Creating video...")
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))

lines = [line.strip() for line in bio_text.replace("\n", " ").split("।") if line.strip()]
frames_per_line = (VIDEO_DURATION * FPS) // max(len(lines), 1)

try:
    font = ImageFont.truetype(FONT_PATH, 36)
except IOError:
    print(f"❌ Font not found at {FONT_PATH}. Provide a valid Devanagari font.")
    exit()

for line in lines:
    img_file = random.choice(images)
    img = Image.open(img_file).resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    bbox = font.getbbox(line)
    line_w, line_h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pos = ((WIDTH - line_w)//2, HEIGHT//2 - line_h//2)
    draw.text(pos, line, font=font, fill=(255,255,255))
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for _ in range(frames_per_line):
        video.write(frame)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 5: Generate AI TTS in Hindi (High Pitch)
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
    pitch=10  # Increased pitch
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
# Step 6: Merge Video + Audio
# -----------------------------
print("🔀 Merging video and audio...")
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

creds = google.oauth2.credentials.Credentials(
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
