import os
import cv2
import requests
import wikipedia
import random
import subprocess
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import texttospeech

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280   # 9:16 Vertical
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
BIO_DURATION = 55  # seconds
NUM_IMAGES = 5

# -----------------------------
# Step 0: Set up Google TTS
# -----------------------------
print("🔧 Setting up Google Cloud TTS client...")
tts_json = os.environ["TTS"]
with open("tts.json", "w", encoding="utf-8") as f:
    f.write(tts_json)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts.json"

tts_client = texttospeech.TextToSpeechClient()
print("✅ TTS client ready!")

# -----------------------------
# Step 1: Fetch Biography Text (Hindi)
# -----------------------------
print("📖 Fetching Gandhi Ji biography from Hindi Wikipedia...")
wikipedia.set_lang("hi")
bio_text = wikipedia.summary("महात्मा गांधी", sentences=5)
print("✅ Biography fetched in Hindi!")

# -----------------------------
# Step 2: Download Images (ensure at least 5)
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/1e/Gandhi_seated.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/91/Gandhi_laughing.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/72/Gandhi_Spinning_Wheel.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/0/0e/Mahatma_Gandhi_1942.jpg"
]

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
            print(f"⚠️ Failed {url}, status code {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

# If fewer than NUM_IMAGES, repeat random images
while len(image_files) < NUM_IMAGES:
    image_files.append(random.choice(image_files))

# -----------------------------
# Step 3: Generate Video with Images + Centered Hindi Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = BIO_DURATION * FPS // len(image_files)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Split bio into shorter lines for readability
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
# Step 4: Generate AI Voiceover (Hindi) with Pitch Up
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
# split bio_text into chunks < 4800 bytes
chunks = []
chunk = ""
for word in bio_text.split():
    if len((chunk + " " + word).encode("utf-8")) < 4800:
        chunk += " " + word
    else:
        chunks.append(chunk.strip())
        chunk = word
if chunk:
    chunks.append(chunk.strip())

with open(AUDIO_FILENAME, "wb") as out:
    for chunk_text in chunks:
        synthesis_input = texttospeech.SynthesisInput(text=chunk_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=4.0  # increase pitch
        )
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
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

request_body = {
    "snippet": {
        "title": "महात्मा गांधी की 50 सेकंड जीवनी #Shorts",
        "description": safe_description + "\n\n#Shorts #MahatmaGandhi #History",
        "tags": ["महात्मा गांधी", "जीवनी", "Shorts", "इतिहास"],
        "categoryId": "22"
    },
    "status": {"privacyStatus": "public"}
}

media = FINAL_FILENAME

upload = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = upload.execute()
print("✅ Upload complete!")
print("📺 Video link: https://www.youtube.com/watch?v=" + response["id"])
