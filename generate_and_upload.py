import os
import io
import cv2
import requests
import wikipedia
import subprocess
from pydub import AudioSegment
from google.cloud import texttospeech
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280  # Vertical 9:16 for Shorts
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
VIDEO_DURATION = 50  # seconds total
MAX_CHARS_PER_LINE = 20

# -----------------------------
# Step 0: Setup Google TTS Client
# -----------------------------
print("🔧 Setting up Google Cloud TTS client...")
tts_json = os.environ["TTS"]
with open("tts_creds.json", "w", encoding="utf-8") as f:
    f.write(tts_json)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts_creds.json"
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
# Step 2: Split bio into chunks for TTS and video frames
# -----------------------------
def split_text(text, max_bytes=4000):
    chunks = []
    current = ""
    for word in text.split():
        if len((current + " " + word).encode("utf-8")) < max_bytes:
            current += " " + word
        else:
            chunks.append(current.strip())
            current = word
    if current:
        chunks.append(current.strip())
    return chunks

tts_chunks = split_text(bio_text, max_bytes=4000)
num_chunks = len(tts_chunks)
frames_per_chunk = VIDEO_DURATION * FPS // num_chunks

# -----------------------------
# Step 3: Fetch Images
# -----------------------------
print("🖼️ Downloading images...")
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/d/d1/Portrait_Gandhi.jpg"
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
# Step 4: Generate Video with Centered Text
# -----------------------------
print("🎬 Creating video...")
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.0
thickness = 2

def wrap_text(text, max_chars=MAX_CHARS_PER_LINE):
    words = text.split()
    lines = []
    line = ""
    for w in words:
        if len((line + " " + w).strip()) <= max_chars:
            line += " " + w
        else:
            lines.append(line.strip())
            line = w
    if line:
        lines.append(line.strip())
    return lines

for chunk in tts_chunks:
    overlay_lines = wrap_text(chunk)
    for img_file in image_files:
        img = cv2.imread(img_file)
        img = cv2.resize(img, (WIDTH, HEIGHT))
        overlay = img.copy()

        total_text_height = len(overlay_lines) * 40
        start_y = HEIGHT // 2 - total_text_height // 2

        for i, line_text in enumerate(overlay_lines):
            (text_w, text_h), _ = cv2.getTextSize(line_text, font, font_scale, thickness)
            pos = (WIDTH // 2 - text_w // 2, start_y + i * 40)
            cv2.putText(overlay, line_text, pos, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        for _ in range(frames_per_chunk):
            video.write(overlay)

video.release()
print("✅ Video created!")

# -----------------------------
# Step 5: Generate AI Voiceover in Hindi (chunked)
# -----------------------------
print("🎙️ Generating AI voiceover in Hindi...")
audio_segments = []

for chunk in tts_chunks:
    synthesis_input = texttospeech.SynthesisInput(text=chunk)
    voice = texttospeech.VoiceSelectionParams(
        language_code="hi-IN",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    segment = AudioSegment.from_file(io.BytesIO(response.audio_content), format="mp3")
    audio_segments.append(segment)

final_audio = sum(audio_segments)
final_audio.export(AUDIO_FILENAME, format="mp3")
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
        "status": {
            "privacyStatus": "public"
        }
    },
    media_body=FINAL_FILENAME
)

response = request.execute()
print(f"✅ Uploaded as Short! Video ID: {response['id']}")
