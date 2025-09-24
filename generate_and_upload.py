import os
import requests
import wikipedia
import random
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from google.cloud import texttospeech
import subprocess
import json

# ========== CONFIG ==========
FONT_PATH = "NotoSansDevanagari-Regular.ttf"  # upload this to repo
TARGET_DURATION = 55  # target ~55 sec
NUM_IMAGES = 5
# ============================

# Setup Google TTS
print("🔧 Setting up Google Cloud TTS client...")
tts_json = os.environ["TTS"]
with open("tts.json", "w") as f:
    f.write(tts_json)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts.json"
tts_client = texttospeech.TextToSpeechClient()
print("✅ TTS client ready!")

# Fetch Biography
print("📖 Fetching Gandhi Ji biography from Hindi Wikipedia...")
wikipedia.set_lang("hi")
biography = wikipedia.summary("महात्मा गांधी", sentences=20)

# Limit biography for ~55 sec audio (~700-800 chars in Hindi speech)
biography = biography[:800]
print("✅ Biography fetched in Hindi!")

# Download images (ensure 5 valid)
print("🖼️ Downloading images...")
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
