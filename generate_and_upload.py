import os
import cv2
import random
import requests
import subprocess
import google.generativeai as genai
from google.cloud import texttospeech
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280  # 9:16 Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 55  # seconds

IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# -----------------------------
# Gemini AI Setup
# -----------------------------
genai.api_key = os.environ["GEMINI_API_KEY"]

print("🔧 Generating Gandhi Ji biography with Gemini AI...")
bio_resp = genai.text.generate(
    model="text-bison-001",
    prompt="50-second biography of Mahatma Gandhi in Hindi, simple and engaging"
)
bio_text = bio_resp.text
print("✅ Biography generated!")

# -----------------------------
# Gemini AI Image Generation
# -----------------------------
print("🖼️ Generating images with Gemini AI...")
image_resp = genai.images.generate(
    model="image-bison-001",
    prompt="Mahatma Gandhi, historical portrait, realistic style",
    size="720x1280",
    n=5
)
image_urls = [img.url for img in image_resp.images]

image_files = []
for i, url in enumerate(image_urls):
    img_path = os.path.join(IMAGE_FOLDER, f"gandhi_{i}.png")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(r.content)
            image_files.append(img_path)
            print(f"✅ Downloaded: {img_path}")
    except Exception as e:
        print(f"⚠️ Failed {url}: {e}")

# Fallback: repeat images if less than 5
while len(image_files) < 5:
    image_files.append(random.choice(image_files))

# -----------------------------
# Generate Video
# -----------------------------
print("🎬 Creating video...")
frames_per_image = (VIDEO_DURATION * FPS) // len(image_files)
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Wrap Hindi text
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
# Google Cloud TTS (Hindi, pitch up)
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
tts_client = texttospeech.TextToSpeechClient()
synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    pitch=6.0  # raise pitch
)
response = tts_client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)
with open(AUDIO_FILENAME, "wb") as out:
    out.write(response.audio_content)
print("✅ AI Hindi audio generated!")

# -----------------------------
# Merge Video + Audio
# -----------------------------
print("🔀 Merging video and audio...")
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac", FINAL_FILENAME
], check=True)
print("✅ Final video ready!")

# -----------------------------
# Upload to YouTube
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
import google.auth.transport.requests
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
        "status": {
            "privacyStatus": "public"
        }
    },
    media_body=FINAL_FILENAME
)
response = request.execute()
print(f"✅ Upload complete! 🎥 Video link: https://www.youtube.com/watch?v={response['id']}")
