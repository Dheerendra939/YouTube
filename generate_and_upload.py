import os
import cv2
import requests
import subprocess
from google.cloud import texttospeech
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import openai

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280   # Vertical 9:16 for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
BIO_DURATION = 60  # seconds

# -----------------------------
# Step 0: Setup OpenAI API
# -----------------------------
openai.api_key = os.environ["OPENAI_API_KEY"]

# -----------------------------
# Step 1: Generate AI Biography in Hindi
# -----------------------------
print("📝 Generating AI biography in Hindi...")
response = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a concise 1-minute biography of Mahatma Gandhi in Hindi."}
    ],
    max_tokens=500
)
bio_text = response.choices[0].message.content.strip()
print("✅ Biography fetched in Hindi!")

# -----------------------------
# Step 2: Download Images
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/14/Mahatma-Gandhi%2C_studio%2C_1931.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/76/MKGandhi.jpg"
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
            print(f"⚠️ Failed to download {url}, status code: {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

if not image_files:
    raise RuntimeError("❌ No images available for video.")

# -----------------------------
# Step 3: Generate Video with Centered Hindi Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = BIO_DURATION * FPS // len(image_files)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Wrap bio text into shorter lines
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
# Step 4: Generate AI Voiceover in Hindi (Google Cloud TTS)
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
import json
tts_json = json.loads(os.environ["TTS"])  # Secret JSON from GitHub
client = texttospeech.TextToSpeechClient.from_service_account_info(tts_json)

synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

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
# Step 6: Upload to YouTube Shorts
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
            "title": "महात्मा गांधी की 1 मिनट जीवनी #Shorts",
            "description": safe_description + "\n\n#Shorts #MahatmaGandhi #History",
            "tags": ["महात्मा गांधी", "जीवनी", "Shorts", "इतिहास"],
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=FINAL_FILENAME
)
response = request.execute()
print(f"✅ Uploaded as Short! Video ID: {response['id']}")    max_tokens=600)
bio_text = response['choices'][0]['message']['content'].strip()
print("✅ AI biography generated!")

# -----------------------------
# Step 2: Fetch Images
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/14/Mahatma-Gandhi%2C_studio%2C_1931.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/76/MKGandhi.jpg"
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
            print(f"⚠️ Failed to download {url}, status code: {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

if not image_files:
    raise RuntimeError("❌ No images available for video.")

# -----------------------------
# Step 3: Generate Video with Text
# -----------------------------
print("🎬 Creating video...")
frames_per_image = BIO_DURATION * FPS // len(image_files)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

# Split text into smaller lines
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
        print(f"⚠️ Skipping {img_file} (invalid image).")
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
# Step 4: Generate AI TTS using Google Cloud
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
tts_json = os.environ["TTS"]
with open("tts.json", "w") as f:
    f.write(tts_json)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts.json"

client = texttospeech_v1.TextToSpeechClient()
synthesis_input = texttospeech_v1.SynthesisInput(text=bio_text)
voice = texttospeech_v1.VoiceSelectionParams(
    language_code="hi-IN",
    ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE
)
audio_config = texttospeech_v1.AudioConfig(audio_encoding=texttospeech_v1.AudioEncoding.MP3)

response = client.synthesize_speech(
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
# -----------------------------
# Step 6: Upload to YouTube Shorts
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
            "title": "महात्मा गांधी की 1 मिनट जीवनी #Shorts",
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
