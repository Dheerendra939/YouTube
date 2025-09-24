import os
import cv2
import requests
import random
import subprocess
from google.cloud import texttospeech
import google.generativeai as genai

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280  # Vertical 9:16 for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 55  # seconds, adjust to 50-59

# -----------------------------
# Setup Gemini AI
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.api_key = os.environ["GEMINI_API_KEY"]
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate Short Biography in Hindi
# -----------------------------
print("📖 Generating short Gandhi Ji biography in Hindi...")
bio_resp = genai.Completion.create(
    model="text-bison-001",
    prompt="Write a short biography of Mahatma Gandhi in Hindi, 50 seconds reading time.",
    temperature=0.7,
    max_output_tokens=500
)
bio_text = bio_resp.completions[0].text.strip()
print("✅ Biography generated!")

# -----------------------------
# Step 2: Generate Images using Gemini AI
# -----------------------------
print("🖼️ Generating images...")
img_resp = genai.Image.create(
    model="image-bison-001",
    prompt="Mahatma Gandhi realistic portrait",
    size="720x1280",
    n=5
)
image_files = []
os.makedirs("images", exist_ok=True)
for idx, img in enumerate(img_resp.images):
    img_path = f"images/gandhi_{idx}.png"
    # Download the generated image
    r = requests.get(img.uri, timeout=10)
    if r.status_code == 200:
        with open(img_path, "wb") as f:
            f.write(r.content)
        image_files.append(img_path)
        print(f"✅ Downloaded: {img_path}")
if not image_files:
    raise RuntimeError("❌ No images available for video.")

# -----------------------------
# Step 3: Generate Video with Images + Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = VIDEO_DURATION * FPS // len(image_files)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Split text into short lines for readability
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

for img_file in image_files:
    img = cv2.imread(img_file)
    img = cv2.resize(img, (WIDTH, HEIGHT))
    overlay = img.copy()

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
# Step 4: Generate AI Voiceover with Google Cloud TTS
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
tts_client = texttospeech.TextToSpeechClient()
synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE,
    pitch=2.0  # pitch increase
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)
response = tts_client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)
with open(AUDIO_FILENAME, "wb") as out:
    out.write(response.audio_content)
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

safe_description = bio_text.replace("\n", " ")[:4500]
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
