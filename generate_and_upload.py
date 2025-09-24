import os
import random
import requests
import wikipedia
import cv2
import numpy as np
from google.cloud import texttospeech
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import re

# -----------------------------
# Google Cloud TTS Setup
# -----------------------------
print("🔧 Setting up Google Cloud TTS client...")
tts_json = os.environ["TTS"]
with open("tts_key.json", "w") as f:
    f.write(tts_json)

credentials = service_account.Credentials.from_service_account_file("tts_key.json")
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
print("✅ TTS client ready!")

# -----------------------------
# Fetch Biography in Hindi
# -----------------------------
person = "महात्मा गांधी"
print(f"📖 Fetching {person} biography from Hindi Wikipedia...")
wikipedia.set_lang("hi")
bio = wikipedia.summary(person, sentences=6)
bio = re.sub(r"\([^)]*\)", "", bio)  # remove brackets
print("✅ Biography fetched in Hindi!")

# -----------------------------
# Text to Speech (Hindi, with pitch)
# -----------------------------
print("🎙️ Generating narration...")
synthesis_input = texttospeech.SynthesisInput(text=bio)

voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    name="hi-IN-Wavenet-D"  # Google Wavenet voice
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    pitch=2.0,  # Raise pitch
    speaking_rate=1.0
)

response = tts_client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)

with open("narration.mp3", "wb") as out:
    out.write(response.audio_content)
print("✅ Narration saved as narration.mp3")

# -----------------------------
# Download Gandhi Images
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/5/5d/Mahatma-Gandhi%2C_studio%2C_1931.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/76/MKGandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/b/bd/Mahatma-Gandhi%2C_London%2C_1931.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/14/Mahatma-Gandhi_seated.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/6/6e/Mahatma_Gandhi_portrait.jpg",
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
            print(f"⚠️ Failed {url}, status {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

# Guarantee at least 5 images
if len(image_files) < 5:
    if image_files:
        while len(image_files) < 5:
            image_files.append(random.choice(image_files))
    else:
        raise RuntimeError("❌ Could not fetch any images for video.")

print(f"✅ Using {len(image_files)} images for video.")

# -----------------------------
# Create Video with Images + Text
# -----------------------------
print("🎬 Creating video...")

audio_duration = 55  # seconds (target length 50–59 sec)
fps = 30
frame_size = (720, 1280)  # portrait 9:16
out = cv2.VideoWriter("output.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, frame_size)

# Split bio text into smaller lines for subtitles
words = bio.split(" ")
lines, current = [], ""
for w in words:
    if len(current) + len(w) < 25:
        current += " " + w
    else:
        lines.append(current.strip())
        current = w
lines.append(current.strip())

frames_per_image = (audio_duration * fps) // len(image_files)

for idx, img_path in enumerate(image_files):
    img = cv2.imread(img_path)
    img = cv2.resize(img, frame_size)

    for _ in range(frames_per_image):
        frame = img.copy()

        # Choose subtitle line
        line = lines[idx % len(lines)]

        # Center text
        font = cv2.FONT_HERSHEY_SIMPLEX
        textsize = cv2.getTextSize(line, font, 1.2, 2)[0]
        x = (frame.shape[1] - textsize[0]) // 2
        y = (frame.shape[0] + textsize[1]) // 2

        cv2.putText(frame, line, (x, y), font, 1.2, (255, 255, 255), 3, cv2.LINE_AA)

        out.write(frame)

out.release()
print("✅ Video created: output.mp4")

# -----------------------------
# Upload to YouTube
# -----------------------------
print("📤 Uploading video to YouTube...")

CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token",
)

youtube = build("youtube", "v3", credentials=creds)

request_body = {
    "snippet": {
        "categoryId": "22",
        "title": f"{person} Biography in Hindi #shorts",
        "description": f"{person} की 59 सेकंड की जीवनी।",
        "tags": ["Biography", "Gandhi", "Hindi", "Shorts"],
    },
    "status": {"privacyStatus": "public"},
}

media = MediaFileUpload("output.mp4", chunksize=-1, resumable=True)

upload = youtube.videos().insert(
    part="snippet,status", body=request_body, media_body=media
)
response = upload.execute()
print("✅ Upload complete!")
print("📺 Video link: https://www.youtube.com/watch?v=" + response["id"])print("🖼️ Downloading images...")
img_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_MK_Gandhi.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/1e/Gandhi_seated.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/91/Gandhi_laughing.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/72/Gandhi_Spinning_Wheel.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/0/0e/Mahatma_Gandhi_1942.jpg"
]

images = []
for i, url in enumerate(img_urls):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            fname = f"images/gandhi_{i}.jpg"
            os.makedirs("images", exist_ok=True)
            with open(fname, "wb") as f:
                f.write(r.content)
            images.append(fname)
            print(f"✅ Downloaded: {fname}")
        else:
            print(f"⚠️ Failed {url}, status {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

# If fewer than 5, repeat existing ones
while len(images) < NUM_IMAGES:
    images.append(random.choice(images))

# Create video with Hindi text
print("🎬 Creating video...")
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter("video.mp4", fourcc, 1, (720, 1280))

font = ImageFont.truetype(FONT_PATH, 48)

for img_path in images:
    img = Image.open(img_path).convert("RGB")
    img = img.resize((720, 1280))

    # Add Hindi biography text overlay
    draw = ImageDraw.Draw(img)
    text = "महात्मा गांधी"
    text_w, text_h = draw.textsize(text, font=font)
    draw.text(((720 - text_w) / 2, 50), text, font=font, fill=(255, 255, 255))

    frame = np.array(img)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    for _ in range(int(TARGET_DURATION / NUM_IMAGES)):
        video.write(frame)

video.release()
print("✅ Video created!")

# Generate TTS with pitch adjustment
print("🎙️ Generating AI voiceover in Hindi...")
synthesis_input = texttospeech.SynthesisInput(
    ssml=f"<speak><prosody pitch='+2st'>{biography}</prosody></speak>"
)
voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

response = tts_client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

with open("audio.mp3", "wb") as out:
    out.write(response.audio_content)
print("✅ AI Hindi audio generated!")

# Merge audio + video
print("🔀 Merging video and audio...")
subprocess.run([
    "ffmpeg", "-y", "-i", "video.mp4", "-i", "audio.mp3",
    "-c:v", "copy", "-c:a", "aac", "-shortest", "short_final.mp4"
])
print("✅ Final video ready!")
