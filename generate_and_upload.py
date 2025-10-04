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
from textwrap import wrap
import json
from pydub import AudioSegment
import math
import time

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
# Topic management (no change)
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
    """Append topic to used.txt safely."""
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
# Gemini / LLM helpers
# -----------------------------
print("🔧 Setting up Gemini AI...")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# model selection — stick to the one that works in your environment
LLM = genai.GenerativeModel("gemini-2.5-flash")
print("✅ Gemini AI ready!")

def llm_generate(prompt, max_output_chars=800):
    try:
        resp = LLM.generate_content(prompt)
        txt = getattr(resp, "text", None)
        if txt is None:
            # some older wrappers may return different shape
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

# Hook (one line) - attention-grabbing
hook_prompt = f"Write one very short, punchy opening HOOK in Hindi (1 line) for a short about {topic}."
hook = llm_generate(hook_prompt).splitlines()[0][:80]

# Title
title_prompt = f"Create a clickable YouTube Shorts title in Hindi for {topic}. Keep under 55 characters , only title not any explanation."
title = llm_generate(title_prompt).splitlines()[0][:55]

# Description + CTA + hashtags
desc_prompt = (
    f"Write a short YouTube description in Hindi for a 55s short about {topic}. "
    "Include a 1-line call-to-action (subscribe/watch more) and 5 trending hashtags at the end."
)
description = llm_generate(desc_prompt)
if not description:
    description = f"{topic} की 55 सेकंड की प्रेरणादायक जीवनी।\n\n#Shorts #Motivation"

# Tags (20) — return comma separated, we'll split and trim
tags_prompt = f"Provide 20 short tags/keywords (comma-separated) in Hindi or English for a short about {topic}."
tags_text = llm_generate(tags_prompt)
tags = [t.strip() for t in tags_text.replace("\n",",").split(",") if t.strip()][:20]
if not tags:
    tags = [topic, "जीवनी", "Motivation", "Shorts"]

print(f"Hook: {hook}")
print(f"Title: {title}")
print(f"Tags: {tags[:10]}... (total {len(tags)})")

# -----------------------------
# Step 2: Fetch images (Google Custom Search + Pexels fallback)
# -----------------------------
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")

def fetch_google_images(query, num=10):
    images = []
    if not GOOGLE_KEY or not GOOGLE_CX:
        print("❌ GOOGLE_API_KEY or GOOGLE_CX missing, skipping Google fetch")
        return images
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"q": query, "cx": GOOGLE_CX, "key": GOOGLE_KEY,
                  "searchType": "image", "num": num, "imgSize": "large", "safe": "high"}
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if "error" in data:
            print("❌ Google Images API error:", data["error"].get("message"))
            return images
        for idx, item in enumerate(data.get("items", [])):
            link = item.get("link")
            if not link:
                continue
            try:
                resp = requests.get(link, timeout=12)
                fname = f"images/google_{idx}.jpg"
                with open(fname, "wb") as f:
                    f.write(resp.content)
                if os.path.getsize(fname) > 1024:
                    images.append(fname)
                    print(f"✅ Google: {fname}")
            except Exception as e:
                print(f"⚠️ Failed to download google image: {e}")
    except Exception as e:
        print("❌ Exception fetching Google images:", e)
    return images

def fetch_pexels_images(query, num=10):
    images = []
    if not PEXELS_KEY:
        print("❌ PEXELS_API_KEY missing, skipping Pexels fetch")
        return images
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = "https://api.pexels.com/v1/search"
        params = {"query": query, "per_page": num}
        r = requests.get(url, headers=headers, params=params, timeout=15)
        data = r.json()
        for idx, photo in enumerate(data.get("photos", [])):
            link = photo["src"].get("large") or photo["src"].get("original")
            if not link: continue
            try:
                resp = requests.get(link, timeout=12)
                fname = f"images/pexels_{idx}.jpg"
                with open(fname, "wb") as f:
                    f.write(resp.content)
                if os.path.getsize(fname) > 1024:
                    images.append(fname)
                    print(f"✅ Pexels: {fname}")
            except Exception as e:
                print(f"⚠️ Failed Pexels download: {e}")
    except Exception as e:
        print("❌ Exception fetching Pexels images:", e)
    return images

def get_images(query, num=10):
    images = fetch_google_images(query, num)
    if len(images) < num:
        extra = fetch_pexels_images(query, num - len(images))
        images.extend(extra)
    if len(images) < 5:
        raise Exception(f"❌ Not enough images (got {len(images)}). Check API keys and network.")
    return images

images = get_images(topic, 10)
print(f"✅ Got {len(images)} images")

# -----------------------------
# Helper: crop to fill (no stretch)
# -----------------------------
def crop_to_frame(img, width, height):
    img = img.convert("RGB")
    im_w, im_h = img.size
    target_ratio = width / height
    img_ratio = im_w / im_h
    if img_ratio > target_ratio:
        new_w = int(im_h * target_ratio)
        left = (im_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, im_h))
    else:
        new_h = int(im_w / target_ratio)
        top = (im_h - new_h) // 2
        img = img.crop((0, top, im_w, top + new_h))
    return img.resize((width, height), Image.LANCZOS)

# -----------------------------
# Step 3: Generate TTS (Google)
# -----------------------------
print("🎙️ Generating Hindi voiceover...")
tts_json = os.environ.get("TTS")
if not tts_json:
    raise SystemExit("❌ TTS secret not found (service account JSON expected in TTS env var).")

credentials_info = json.loads(tts_json)
credentials = service_account.Credentials.from_service_account_info(credentials_info)
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

synthesis_input = texttospeech.SynthesisInput(text=bio_text)
voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE)
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, pitch=-6)

resp = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
with open(AUDIO_FILENAME, "wb") as f:
    f.write(resp.audio_content)
print("✅ Voiceover ready!")

# load voice to measure length
narration = AudioSegment.from_file(AUDIO_FILENAME)
audio_ms = len(narration)
audio_seconds = audio_ms / 1000.0
frames_total = int(round(audio_seconds * FPS))
print(f"🎧 Narration length: {audio_seconds:.2f}s, frames: {frames_total}")

# -----------------------------
# Step 4: Create video (zoom effect, double time per image but match narration)
# -----------------------------
print("🎬 Creating video (zoom effect) ...")
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))

# We'll use fewer images if narration is short: compute frames per image so we finish exactly on narration.
# We double the base image display time as requested: base_frames = frames_total // len(images)
base_frames = max(1, frames_total // len(images))
frames_per_image = base_frames * 2

# But we must ensure total frames == frames_total: adjust frames_per_image (distribute remainder)
total_frames_needed = frames_total
frames_generated = 0
remaining_images = len(images)

for idx, img_file in enumerate(images):
    # compute frames for this image (distribute remainder so sum == total_frames_needed)
    frames_for_this = min(frames_per_image, total_frames_needed - frames_generated - (remaining_images - 1))
    remaining_images -= 1

    img_base = Image.open(img_file)
    img_base = crop_to_frame(img_base, WIDTH, HEIGHT)

    # zoom animation for frames_for_this frames
    for f in range(frames_for_this):
        # use a gentle in-out zoom between 1.0 and 1.08
        t = f / max(1, frames_for_this - 1)
        zoom = 1.0 + 0.08 * (0.5 - 0.5 * math.cos(math.pi * t))  # ease-in-out
        w = int(WIDTH * zoom)
        h = int(HEIGHT * zoom)
        img = img_base.resize((w, h), Image.LANCZOS)
        left = (w - WIDTH) // 2
        top = (h - HEIGHT) // 2
        img_cropped = img.crop((left, top, left + WIDTH, top + HEIGHT)).convert("RGB")
        frame = cv2.cvtColor(np.array(img_cropped), cv2.COLOR_RGB2BGR)
        video.write(frame)
        frames_generated += 1
        if frames_generated >= total_frames_needed:
            break
    if frames_generated >= total_frames_needed:
        break

# If not enough frames (rare), pad with last image
while frames_generated < total_frames_needed:
    last_img = Image.open(images[-1])
    last_img = crop_to_frame(last_img, WIDTH, HEIGHT)
    frame = cv2.cvtColor(np.array(last_img), cv2.COLOR_RGB2BGR)
    video.write(frame)
    frames_generated += 1

video.release()
print(f"✅ Video created: {VIDEO_FILENAME} (frames: {frames_generated})")

# -----------------------------
# Step 5: Add background music (mix)
# -----------------------------
print("🎵 Adding background music...")
voice_seg = narration
try:
    bgm = AudioSegment.from_file(BGM_PATH)
except Exception as e:
    print("⚠️ Could not load background music:", e)
    bgm = AudioSegment.silent(duration=audio_ms)

# reduce bgm level (you can tweak this value: -12 to -6 is common)
bgm = bgm - 12
if len(bgm) < len(voice_seg):
    bgm = bgm * (len(voice_seg) // len(bgm) + 1)
bgm = bgm[:len(voice_seg)]

final_mix = voice_seg.overlay(bgm)
final_mix.export(AUDIO_FILENAME, format="mp3")
print("✅ Background music mixed into narration")

# -----------------------------
# Step 6: Thumbnail creation (hook/title overlay)
# -----------------------------
print("🖼️ Creating thumbnail image...")
try:
    thumb_img = Image.open(images[0]).convert("RGB")
    thumb_img = crop_to_frame(thumb_img, 1280, 720)  # YouTube prefers 1280x720
    draw = ImageDraw.Draw(thumb_img)
    try:
        thumb_font = ImageFont.truetype(FONT_PATH, 72)
    except Exception:
        thumb_font = ImageFont.load_default()

    # Compose a compact headline using the hook (fallback to title)
    headline = hook if hook else title
    # wrap headline
    lines = wrap(headline, width=18)
    # draw semi-transparent rectangle behind text
    rect_h = 80 * len(lines) + 40
    rect_w = thumb_img.width - 80
    rect_x = 40
    rect_y = thumb_img.height - rect_h - 40
    overlay = Image.new("RGBA", thumb_img.size, (0,0,0,0))
    ol_draw = ImageDraw.Draw(overlay)
    ol_draw.rectangle((rect_x, rect_y, rect_x+rect_w, rect_y+rect_h), fill=(0,0,0,150))
    # draw text
    y = rect_y + 20
    for ln in lines:
        w,h = ol_draw.textsize(ln, font=thumb_font)
        ol_draw.text((rect_x + (rect_w - w)//2, y), ln, font=thumb_font, fill=(255,255,255,255))
        y += h + 6
    thumb_final = Image.alpha_composite(thumb_img.convert("RGBA"), overlay)
    thumb_final = thumb_final.convert("RGB")
    thumb_final.save(THUMBNAIL_FILENAME, quality=85)
    print(f"✅ Thumbnail saved to {THUMBNAIL_FILENAME}")
except Exception as e:
    print("⚠️ Thumbnail creation failed:", e)

# -----------------------------
# Step 7: Merge video + audio (ffmpeg)
# -----------------------------
print("🔀 Merging video + audio into final file...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", VIDEO_FILENAME,
    "-i", AUDIO_FILENAME,
    "-c:v", "copy", "-c:a", "aac",
    FINAL_FILENAME
], check=True)
print(f"✅ Final video: {FINAL_FILENAME}")

# -----------------------------
# Step 8: Create SRT (simple split) and try to upload captions
# -----------------------------
def make_srt(text, audio_len_ms, out_filename=SRT_FILENAME):
    # split by danda (Hindi) or punctuation
    sentences = []
    if "।" in text:
        parts = [p.strip() for p in text.split("।") if p.strip()]
    else:
        parts = [p.strip() for p in text.replace("\n"," ").split(".") if p.strip()]
    if not parts:
        parts = [text]
    # distribute timings proportional to length
    total_chars = sum(len(p) for p in parts)
    srt_lines = []
    cursor_ms = 0
    for idx, p in enumerate(parts, start=1):
        portion = len(p) / max(1, total_chars)
        dur_ms = max(300, int(portion * audio_len_ms))
        start_ms = cursor_ms
        end_ms = min(audio_len_ms, cursor_ms + dur_ms)
        # format times
        def fmt(ms):
            h = ms // 3600000
            m = (ms % 3600000) // 60000
            s = (ms % 60000) // 1000
            ms_rem = ms % 1000
            return f"{h:02d}:{m:02d}:{s:02d},{ms_rem:03d}"
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{fmt(start_ms)} --> {fmt(end_ms)}")
        srt_lines.append(p.strip())
        srt_lines.append("")
        cursor_ms = end_ms
    with open(out_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    return out_filename

srt_file = make_srt(bio_text, audio_ms)
print(f"✅ SRT generated: {srt_file}")

# -----------------------------
# Step 9: Upload to YouTube
# -----------------------------
print("📤 Uploading to YouTube...")
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")
if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
    raise SystemExit("❌ YouTube OAuth info missing in env")

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
try:
    creds.refresh(google.auth.transport.requests.Request())
except Exception as e:
    print("❌ Failed to refresh YouTube credentials:", e)
    raise

youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

safe_description = f"{description}\n\nSubscribe for more shorts! 🔔"

# prepare upload
media = MediaFileUpload(FINAL_FILENAME, chunksize=-1, resumable=True, mimetype='video/mp4')
request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": title,
            "description": safe_description[:4500],
            "tags": tags,
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=media
)

print("▶️ Starting upload (this may take a while)...")
response = None
try:
    response = request.execute()
    video_id = response.get("id")
    print(f"✅ Upload complete! Video: https://www.youtube.com/watch?v={video_id}")
except Exception as e:
    print("❌ Upload failed:", e)
    raise

# set thumbnail if created
if os.path.exists(THUMBNAIL_FILENAME) and video_id:
    try:
        thumb_media = MediaFileUpload(THUMBNAIL_FILENAME)
        youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
        print("✅ Thumbnail uploaded")
    except Exception as e:
        print("⚠️ Thumbnail upload failed:", e)

# try to upload captions (best-effort)
try:
    # You must have permission to insert captions; API may reject otherwise
    with open(srt_file, "rb") as fh:
        youtube.captions().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": "hi",
                    "name": f"{topic} (auto)",
                    "isDraft": False
                }
            },
            media_body=MediaFileUpload(srt_file, mimetype="application/octet-stream")
        ).execute()
    print("✅ Captions uploaded (may take some time to appear)")
except Exception as e:
    print("⚠️ Caption upload failed (often requires extra permissions):", e)

# -----------------------------
# Step 10: mark topic used
# -----------------------------
mark_topic_as_used(topic)

print("🎉 Done. Keep monitoring analytics and iterate on titles/thumbnails.")
