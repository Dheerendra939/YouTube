import os
import cv2
import requests
import random
import subprocess
import textwrap
from google.cloud import texttospeech
import google.generativeai as genai
import wikipedia

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280  # 9:16 vertical for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
BIO_DURATION = 55  # seconds, within 50-59
MIN_IMAGES = 5

# -----------------------------
# Gemini AI Setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.api_key = os.environ["GEMINI_API_KEY"]
print("✅ Gemini AI ready!")

# -----------------------------
# Step 1: Generate Short Biography (Hindi)
# -----------------------------
prompt = "महात्मा गांधी की 50 सेकंड की संक्षिप्त जीवनी हिंदी में लिखो।"
print("📖 Generating short Gandhi Ji biography in Hindi...")
bio_resp = genai.chat.completions.create(
    model="gemini-1.5",
    messages=[{"author": "user", "content": prompt}],
    temperature=0.7
)
bio_text = bio_resp.response[0].content[0].text
print("✅ Biography generated!")

# -----------------------------
# Step 2: Generate Image Links
# -----------------------------
img_prompt = "महात्मा गांधी से संबंधित 5 तस्वीरों के सार्वजनिक लिंक दो।"
print("🖼️ Generating image links...")
img_resp = genai.chat.completions.create(
    model="gemini-1.5",
    messages=[{"author": "user", "content": img_prompt}],
    temperature=0.7
)
image_urls = []
for line in img_resp.response[0].content[0].text.splitlines():
    if line.startswith("http"):
        image_urls.append(line.strip())
if not image_urls:
    raise RuntimeError("❌ No image URLs from Gemini AI.")
print(f"✅ Got {len(image_urls)} image URLs.")

# -----------------------------
# Step 3: Download Images
# -----------------------------
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)
image_files = []
headers = {"User-Agent": "Mozilla/5.0"}

print("🖼️ Downloading images...")
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
        print(f"⚠️ Error {url}: {e}")

# Fill missing images with repeats if needed
while len(image_files) < MIN_IMAGES:
    image_files.append(random.choice(image_files))

# -----------------------------
# Step 4: Generate Video
# -----------------------------
print("🎬 Creating video...")
frames_per_image = (BIO_DURATION * FPS) // len(image_files)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2
line_height = 40

# Wrap Hindi text into shorter lines
wrapped_lines = textwrap.wrap(bio_text, width=25)

for img_file in image_files:
    img = cv2.imread(img_file)
    if img is None:
        continue
    img = cv2.resize(img, (WIDTH, HEIGHT))
    overlay = img.copy()

    # Vertical center
    total_text_height = len(wrapped_lines) * line_height
    start_y = HEIGHT // 2 - total_text_height // 2

    for i, line in enumerate(wrapped_lines):
        (text_w, text_h), _ = cv2.getTextSize(line, font, font_scale, thickness)
        pos = (WIDTH // 2 - text_w // 2, start_y + i * line_height)
        cv2.putText(overlay, line, pos, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    for _ in range(frames_per_image):
        video.write(overlay)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 5: Google Cloud TTS
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
    pitch=4.0  # higher pitch
)
response = tts_client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)
with open(AUDIO_FILENAME, "wb") as out:
    out.write(response.audio_content)
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
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

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

safe_description = bio_text.replace("\n", " ").replace("\r", "")[:4500]

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
print(f"✅ Upload complete!\n📺 Video link: https://www.youtube.com/watch?v={response['id']}")
