import os
import cv2
import requests
import random
import subprocess
import tempfile
from google.cloud import texttospeech
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import google.auth.transport.requests
import google.generativeai as genai

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280   # Vertical 9:16 for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 50  # seconds
MIN_IMAGES = 5       # minimum images for video

# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.api_key = os.environ.get("GEMINI_API_KEY")
if not genai.api_key:
    raise RuntimeError("❌ GEMINI_API_KEY not found in environment variables.")
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate short biography in Hindi
# -----------------------------
print("📖 Generating short Gandhi Ji biography in Hindi...")
bio_prompt = "50-second biography of Mahatma Gandhi in Hindi."
bio_resp = genai.Completion.create(
    model="models/text-bison-001",
    prompt=bio_prompt,
    temperature=0.7,
    max_output_tokens=500
)
bio_text = bio_resp.output[0].content.strip()
print("✅ Short biography generated in Hindi:")
print(bio_text)

# -----------------------------
# Step 2: Get image URLs from Gemini
# -----------------------------
print("🖼️ Generating image URLs via Gemini...")
img_prompt = "Give 5 copyright-free image URLs of Mahatma Gandhi for educational content."
img_resp = genai.Completion.create(
    model="models/text-bison-001",
    prompt=img_prompt,
    temperature=0.7,
    max_output_tokens=500
)
# Extract URLs from output
img_text = img_resp.output[0].content
image_urls = [line.strip() for line in img_text.splitlines() if line.strip().startswith("http")]
if len(image_urls) < MIN_IMAGES:
    print("⚠️ Not enough URLs, adding fallback images.")
    # fallback URLs
    image_urls += [
        "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/14/Mahatma-Gandhi%2C_studio%2C_1931.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/7/76/MKGandhi.jpg"
    ]
image_urls = image_urls[:MIN_IMAGES]

# -----------------------------
# Step 3: Download images
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)
image_files = []
headers = {"User-Agent": "Mozilla/5.0"}

for i, url in enumerate(image_urls):
    img_path = os.path.join(image_folder, f"gandhi_{i}.jpg")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(r.content)
            image_files.append(img_path)
            print(f"✅ Downloaded: {img_path}")
        else:
            print(f"⚠️ Failed {url}, status code: {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

# Ensure at least MIN_IMAGES by repeating random images if needed
while len(image_files) < MIN_IMAGES:
    image_files.append(random.choice(image_files))

# -----------------------------
# Step 4: Generate video with centered text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = (VIDEO_DURATION * FPS) // len(image_files)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Split text into shorter lines
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
    if img is None:
        continue
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
# Step 5: Generate AI TTS with higher pitch
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
client = texttospeech.TextToSpeechClient()
synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    pitch=5.0  # increase pitch
)
response = client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)
with open(AUDIO_FILENAME, "wb") as out:
    out.write(response.audio_content)
print("✅ AI Hindi audio generated!")

# -----------------------------
# Step 6: Merge video and audio
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

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
creds.refresh(google.auth.transport.requests.Request())
youtube = build("youtube", "v3", credentials=creds)

safe_description = bio_text.replace("\n", " ").replace("\r", " ")
safe_description = safe_description[:4500]

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
print(f"✅ Uploaded as Short! Video ID: {response['id']}")
print(f"📺 Video link: https://www.youtube.com/watch?v={response['id']}")
