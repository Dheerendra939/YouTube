import os
import cv2
import random
import subprocess
import requests
import google.generativeai as genai
from google.cloud import texttospeech

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280   # Vertical 9:16 for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 55  # Target video length in seconds

# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.api_key = os.environ["GEMINI_API_KEY"]
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate Biography in Hindi
# -----------------------------
print("📖 Generating short Gandhi Ji biography in Hindi...")
bio_prompt = "Write a concise biography of Mahatma Gandhi in Hindi suitable for a 50-second YouTube Short."
bio_resp = genai.generate_text(model="text-bison-001", prompt=bio_prompt)
bio_text = bio_resp.text.strip()
print("✅ Biography generated!")

# -----------------------------
# Step 2: Fetch / Generate Images
# -----------------------------
print("🖼️ Fetching images...")

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
    except:
        continue

# If not enough images, generate via Gemini AI
while len(images) < 5:
    img_resp = genai.generate_image(
        model="image-bison-001",
        prompt="Portrait of Mahatma Gandhi, realistic, vertical, high quality"
    )
    img_url = img_resp.images[0].uri
    img_path = os.path.join(image_folder, f"gandhi_gen_{len(images)}.jpg")
    r = requests.get(img_url)
    with open(img_path, "wb") as f:
        f.write(r.content)
    images.append(img_path)
    print(f"✅ Generated image: {img_path}")

# -----------------------------
# Step 3: Create Video with Centered Hindi Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = (VIDEO_DURATION * FPS) // len(images)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Split Hindi bio into short lines
wrapped_lines = []
line = ""
for word in bio_text.split():
    if len(line + " " + word) < 25:
        line += " " + word
    else:
        wrapped_lines.append(line.strip())
        line = word
if line:
    wrapped_lines.append(line.strip())

for img_file in images:
    img = cv2.imread(img_file)
    if img is None:
        continue
    img = cv2.resize(img, (WIDTH, HEIGHT))
    overlay = img.copy()

    # Position lines vertically centered
    total_text_height = len(wrapped_lines) * 40
    start_y = HEIGHT // 2 - total_text_height // 2
    for i, line in enumerate(wrapped_lines):
        (text_w, text_h), _ = cv2.getTextSize(line, font, font_scale, thickness)
        pos = (WIDTH // 2 - text_w // 2, start_y + i * 40)
        cv2.putText(overlay, line, pos, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    for _ in range(frames_per_image):
        video.write(overlay)

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
    pitch=5  # increase pitch
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
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.auth.transport.requests

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
