import os
import requests
import cv2
import numpy as np
import wikipedia
import openai
from google.cloud import texttospeech
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth.transport.requests

# -----------------------------
# Config
# -----------------------------
openai.api_key = os.environ["OPENAI_API_KEY"]
TTS_JSON = os.environ["TTS"]  # Google TTS credentials JSON stored in GitHub secret
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"

# -----------------------------
# Step 1: Generate AI Biography in Hindi
# -----------------------------
print("📝 Generating AI biography in Hindi...")
prompt = """
आप महात्मा गांधी के बारे में एक संक्षिप्त, सरल और प्रभावशाली जीवनी लिखिए।
यह जीवनी लगभग 1 मिनट के भाषण जितनी होनी चाहिए।
सामान्य दर्शकों के लिए प्रेरणादायक और जानकारीपूर्ण अंदाज़ में लिखें।
"""

response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": "आप एक जीवनी लेखक हैं।"},
              {"role": "user", "content": prompt}],
    max_tokens=500
)
bio_text = response.choices[0].message.content.strip()
print("✅ AI Biography generated!")

# -----------------------------
# Step 2: Download images from Wikipedia
# -----------------------------
print("🖼️ Downloading images...")
os.makedirs("images", exist_ok=True)
search = wikipedia.page("Mahatma Gandhi")
image_urls = search.images[:5]
image_files = []

for i, url in enumerate(image_urls):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            filename = f"images/gandhi_{i}.jpg"
            with open(filename, "wb") as f:
                f.write(r.content)
            image_files.append(filename)
            print(f"✅ Downloaded: {filename}")
        else:
            print(f"⚠️ Failed to download {url}")
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

if not image_files:
    raise Exception("❌ No images downloaded, cannot continue.")

# -----------------------------
# Step 3: Create Video Slideshow
# -----------------------------
print("🎬 Creating video...")
height, width = 1280, 720
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, 1, (width, height))

for img_file in image_files:
    img = cv2.imread(img_file)
    if img is None:
        continue
    img = cv2.resize(img, (width, height))
    for _ in range(3):  # show each image for 3 seconds
        video.write(img)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 4: Generate Hindi Voiceover with Google Cloud TTS
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
creds_dict = eval(TTS_JSON)
credentials = service_account.Credentials.from_service_account_info(creds_dict)
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN",
    name="hi-IN-Standard-D",
    ssml_gender=texttospeech.SsmlVoiceGender.MALE,
)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

response_tts = tts_client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)

with open(AUDIO_FILENAME, "wb") as out:
    out.write(response_tts.audio_content)

print("✅ AI Hindi audio generated!")

# -----------------------------
# Step 5: Merge Video and Audio with FFmpeg
# -----------------------------
print("🔀 Merging video and audio...")
os.system(f"ffmpeg -y -i {VIDEO_FILENAME} -i {AUDIO_FILENAME} -shortest -c:v copy -c:a aac {FINAL_FILENAME}")
print("✅ Final video ready!")

# -----------------------------
# Step 6: Upload to YouTube Shorts
# -----------------------------
print("📤 Uploading to YouTube...")

creds = google.oauth2.credentials.Credentials(
    None,
    refresh_token=YOUTUBE_REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=YOUTUBE_CLIENT_ID,
    client_secret=YOUTUBE_CLIENT_SECRET
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
