#!/usr/bin/env python3
import os
import cv2
import random
import subprocess
import requests
import numpy as np
import google.generativeai as genai
from google.cloud import texttospeech
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.auth.transport.requests
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import math

# -----------------------------
# Settings
# -----------------------------
WIDTH, HEIGHT = 720, 1280
FPS = 24
VIDEO_FILENAME = "video.mp4"
AUDIO_FILENAME = "audio.mp3"
FINAL_FILENAME = "short_final.mp4"
BGM_PATH = "background_music.mp3"
FONT_PATH = "NotoSans-Devanagari.ttf"
TOPICS_FILE = "topics.txt"
USED_FILE = "used.txt"
THUMBNAIL_FILENAME = "thumbnail.jpg"
SRT_FILENAME = "captions.srt"

os.makedirs("images", exist_ok=True)

# -----------------------------
# Topic management
# -----------------------------
def get_next_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        all_topics = [line.strip() for line in f if line.strip()]

    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8") as f:
            used = set(line.strip() for line in f if line.strip())
    else:
        used = set()

    available = [t for t in all_topics if t not in used]

    if not available:
        print("❌ All topics used. Resetting used.txt...")
        available = all_topics
        with open(USED_FILE, "w", encoding="utf-8") as f:
            f.write("")  # clear file
        used = set()

    topic = random.choice(available)
    return topic

def mark_topic_as_used(topic):
    try:
        if not os.path.exists(USED_FILE):
            with open(USED_FILE, "w", encoding="utf-8") as f:
                pass
        with open(USED_FILE, "r", encoding="utf-8") as f:
            used_topics = set(line.strip() for line in f if line.strip())
        if topic not in used_topics:
            with open(USED_FILE, "a", encoding="utf-8") as f:
                f.write(topic + "\n")
            print(f"📝 Added '{topic}' to used.txt")
        else:
            print(f"ℹ️ Topic '{topic}' was already in used.txt")
    except Exception as e:
        print(f"❌ Failed to write topic to {USED_FILE}: {e}")

# -----------------------------
# Gemini setup
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
LLM = genai.GenerativeModel("gemini-2.5-flash")
print("✅ Gemini AI ready!")

def llm_generate(prompt, max_output_chars=800):
    try:
        resp = LLM.generate_content(prompt)
        txt = getattr(resp, "text", None)
        if txt is None:
            txt = str(resp)
        return txt.strip()
    except Exception as e:
        print("❌ LLM generation failed:", e)
        return ""

# -----------------------------
# Step 0: choose topic
# -----------------------------
topic = get_next_topic()
print(f"🎯 Selected topic: {topic}")

# -----------------------------
# Step 1: script + hook + title + description + tags
# -----------------------------
print("📖 Generating script, hook, title, description and tags...")

bio_prompt = (
    f"Write a 55 second motivational biography of {topic} in Hindi suitable for a YouTube Short narration. "
    "Keep it concise, emotive, and suitable for voiceover. Do not add headings. Keep the language natural Hindi."
)
bio_text = llm_generate(bio_prompt)
if not bio_text:
    raise SystemExit("❌ LLM failed to produce biography.")

hook_prompt = f"Write one very short, punchy opening HOOK in Hindi (1 line) for a short about {topic}."
hook = llm_generate(hook_prompt).splitlines()[0][:80]

def generate_title(topic):
    title_prompt = (
        f"Suggest a viral YouTube Shorts title under 55 characters "
        f"for a motivational biography about {topic} in Hindi. "
        f"Output only the title, no explanation."
    )
    raw_title = llm_generate(title_prompt)
    lines = [line.strip("-•: ") for line in raw_title.splitlines() if line.strip()]
    if not lines:
        return f"Motivational Story of {topic} #Shorts"
    title = lines[0]
    if len(title) > 55:
        title = title[:52] + "..."
    return title

video_title = generate_title(topic)
print(f"🎬 Generated title: {video_title}")

desc_prompt = (
    f"Write a short YouTube description in Hindi for a 55s short about {topic}. "
    "Include a 1-line call-to-action (subscribe/watch more) and 5 trending hashtags at the end."
)
description = llm_generate(desc_prompt)
if not description:
    description = f"{topic} की 55 सेकंड की प्रेरणादायक जीवनी।\n\n#Shorts #Motivation"

tags_prompt = f"Provide 20 short tags/keywords (comma-separated) in Hindi or English for a short about {topic}."
tags_text = llm_generate(tags_prompt)
tags = [t.strip() for t in tags_text.replace("\n", ",").split(",") if t.strip()][:20]
if not tags:
    tags = [topic, "जीवनी", "Motivation", "Shorts"]

print(f"Hook: {hook}")
print(f"Title: {video_title}")
print(f"Tags: {tags[:10]}... (total {len(tags)})")

# -----------------------------
# Step 2: fetch images (PEXELS or Google Custom Search)
# -----------------------------
print("🖼️ Fetching images...")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")
headers = {"Authorization": PEXELS_KEY}
resp = requests.get(
    f"https://api.pexels.com/v1/search?query={topic}&per_page=10", headers=headers
)
if resp.status_code == 200:
    data = resp.json()
    for idx, photo in enumerate(data.get("photos", [])):
        url = photo["src"]["large"]
        img = requests.get(url).content
        with open(f"images/img{idx}.jpg", "wb") as f:
            f.write(img)
print("✅ Got images")

# -----------------------------
# Step 3: Google TTS
# -----------------------------
print("🎙️ Generating Hindi voiceover...")
client = texttospeech.TextToSpeechClient()
input_text = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(
    language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
with open(AUDIO_FILENAME, "wb") as out:
    out.write(response.audio_content)
print("✅ Voiceover ready!")

# -----------------------------
# Step 4: create video slideshow
# -----------------------------
print("🎬 Creating video with zoom effect...")
images = [cv2.imread(f"images/{f}") for f in os.listdir("images") if f.endswith(".jpg")]
audio = AudioSegment.from_file(AUDIO_FILENAME)
duration_sec = audio.duration_seconds
frame_count = int(duration_sec * FPS)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

frames_per_img = frame_count // max(1, len(images))
for img in images:
    img = cv2.resize(img, (WIDTH, HEIGHT))
    for i in range(frames_per_img):
        zoom = 1 + (i / frames_per_img) * 0.1
        M = cv2.getRotationMatrix2D((WIDTH/2, HEIGHT/2), 0, zoom)
        zoomed = cv2.warpAffine(img, M, (WIDTH, HEIGHT))
        out.write(zoomed)
out.release()
print("✅ Video created!")

# -----------------------------
# Step 5: merge video + audio
# -----------------------------
print("🔀 Merging video + audio...")
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_FILENAME, "-i", AUDIO_FILENAME,
    "-shortest", "-c:v", "libx264", "-c:a", "aac", FINAL_FILENAME
])
print("✅ Final video ready!")

# -----------------------------
# Step 6: thumbnail
# -----------------------------
print("🖼️ Creating thumbnail...")
img = Image.open("images/img0.jpg").resize((WIDTH, HEIGHT))
draw = ImageDraw.Draw(img)
font = ImageFont.truetype(FONT_PATH, 60)
draw.text((50, HEIGHT-150), video_title, font=font, fill="white")
img.save(THUMBNAIL_FILENAME)
print("✅ Thumbnail ready!")

# -----------------------------
# Step 7: captions (SRT)
# -----------------------------
print("✍️ Creating captions...")
words = bio_text.split()
words_per_line = 6
with open(SRT_FILENAME, "w", encoding="utf-8") as f:
    idx = 1
    t = 0.0
    step = duration_sec / (len(words) / words_per_line)
    for i in range(0, len(words), words_per_line):
        line = " ".join(words[i:i+words_per_line])
        start = t
        end = t + step
        f.write(f"{idx}\n")
        f.write(f"00:00:{int(start):02},000 --> 00:00:{int(end):02},000\n")
        f.write(line + "\n\n")
        idx += 1
        t = end
print("✅ Captions ready!")

# -----------------------------
# Step 8: upload to YouTube
# -----------------------------
print("📤 Uploading to YouTube...")
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
creds.refresh(google.auth.transport.requests.Request())
youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

media = MediaFileUpload(FINAL_FILENAME, resumable=True, mimetype="video/mp4")
request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": video_title,
            "description": description[:4500],
            "tags": tags,
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=media
)
response = request.execute()
video_id = response.get("id")
print(f"✅ Upload complete! Video: https://www.youtube.com/watch?v={video_id}")

# -----------------------------
# Step 9: mark topic used
# -----------------------------
mark_topic_as_used(topic)

print("🎉 All steps completed successfully!")
