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
import google.auth.transport.requests  
from PIL import Image  
import json  
from pydub import AudioSegment  
  
# -----------------------------  
# Settings  
# -----------------------------  
WIDTH, HEIGHT = 720, 1280  
FPS = 24  
VIDEO_FILENAME = "video.mp4"  
AUDIO_FILENAME = "audio.mp3"  
FINAL_FILENAME = "short_final.mp4"  
BGM_PATH = "background_music.mp3"  
  
TOPICS_FILE = "topics.txt"  
USED_FILE = "used.txt"  
  
os.makedirs("images", exist_ok=True)  
  
# -----------------------------  
# Step 0: Topic Management  
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
    """Append topic to used.txt and sync it"""  
    try:  
        with open(USED_FILE, "a", encoding="utf-8") as f:  
            f.write(topic + "\n")  
        print(f"📝 Added '{topic}' to used.txt")  
  
        # Optional: sync with git if needed  
        subprocess.run(["git", "add", USED_FILE], check=False)  
        subprocess.run(["git", "commit", "-m", f"Mark {topic} as used"], check=False)  
        subprocess.run(["git", "push"], check=False)  
  
    except Exception as e:  
        print(f"❌ Failed to update {USED_FILE}: {e}")  
  
topic = get_next_topic()  
print(f"🎯 Selected topic: {topic}")  
  
# -----------------------------  
# Gemini AI Setup  
# -----------------------------  
print("🔧 Setting up Gemini AI...")  
genai.configure(api_key=os.environ["GEMINI_API_KEY"])  
gemini_model = genai.GenerativeModel("gemini-2.5-flash")  
print("✅ Gemini AI ready!")  
  
# -----------------------------  
# Step 1: Generate Script  
# -----------------------------  
print(f"📖 Generating biography of {topic} in Hindi...")  
bio_prompt = f"write a 55 second motivational biography of {topic} in Hindi. Keep it for narration only, no extra lines."  
bio_resp = gemini_model.generate_content(bio_prompt)  
bio_text = bio_resp.text.strip()  
print("✅ Script generated!")  
  
# -----------------------------  
# Step 2: Fetch Images  
# -----------------------------  
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")  
GOOGLE_CX = os.getenv("GOOGLE_CX")  
PEXELS_KEY = os.getenv("PEXELS_API_KEY")  
  
def fetch_google_images(query, num=10):  
    images = []  
    try:  
        url = "https://www.googleapis.com/customsearch/v1"  
        params = {"q": query, "cx": GOOGLE_CX, "key": GOOGLE_KEY,  
                  "searchType": "image", "num": num, "imgSize": "large", "safe": "high"}  
        r = requests.get(url, params=params)  
        data = r.json()  
        for idx, item in enumerate(data.get("items", [])):  
            link = item.get("link")  
            if not link: continue  
            try:  
                img = requests.get(link, timeout=10)  
                fname = f"images/google_{idx}.jpg"  
                with open(fname, "wb") as f: f.write(img.content)  
                if os.path.getsize(fname) > 1024: images.append(fname)  
            except: pass  
    except: pass  
    return images  
  
def fetch_pexels_images(query, num=10):  
    images = []  
    try:  
        headers = {"Authorization": PEXELS_KEY}  
        url = "https://api.pexels.com/v1/search"  
        params = {"query": query, "per_page": num}  
        r = requests.get(url, headers=headers, params=params)  
        data = r.json()  
        for idx, photo in enumerate(data.get("photos", [])):  
            link = photo["src"]["large"]  
            try:  
                img = requests.get(link, timeout=10)  
                fname = f"images/pexels_{idx}.jpg"  
                with open(fname, "wb") as f: f.write(img.content)  
                if os.path.getsize(fname) > 1024: images.append(fname)  
            except: pass  
    except: pass  
    return images  
  
def get_images(query, num=10):  
    images = fetch_google_images(query, num)  
    if len(images) < num: images += fetch_pexels_images(query, num-len(images))  
    if len(images) < 5: raise Exception("❌ Not enough images")  
    print(f"✅ Got {len(images)} images")  
    return images  
  
images = get_images(topic, 10)  
  
# -----------------------------  
# Helper: crop image to fill frame  
# -----------------------------  
def crop_to_frame(img, width, height):  
    img = img.convert("RGB")  
    im_w, im_h = img.size  
    target_ratio = width / height  
    img_ratio = im_w / im_h  
    if img_ratio > target_ratio:  
        new_w = int(im_h * target_ratio)  
        left = (im_w - new_w) // 2  
        img = img.crop((left,0,left+new_w,im_h))  
    else:  
        new_h = int(im_w / target_ratio)  
        top = (im_h - new_h) // 2  
        img = img.crop((0,top,im_w,top+new_h))  
    return img.resize((width,height))  
  
# -----------------------------  
# Step 3: Generate TTS  
# -----------------------------  
print("🎙️ Generating Hindi voiceover...")  
tts_json = os.environ["TTS"]  
credentials_info = json.loads(tts_json)  
credentials = service_account.Credentials.from_service_account_info(credentials_info)  
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)  
synthesis_input = texttospeech.SynthesisInput(text=bio_text)  
voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE)  
audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, pitch=-6)  
response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)  
with open(AUDIO_FILENAME, "wb") as f: f.write(response.audio_content)  
print("✅ Voiceover ready!")  
  
voiceover = AudioSegment.from_file(AUDIO_FILENAME)  
audio_duration = len(voiceover)/1000.0  
frames_total = int(audio_duration * FPS)  
  
# -----------------------------  
# Step 4: Create Video with zoom effect  
# -----------------------------  
print("🎬 Creating video with zoom effect matching narration length...")  
video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))  
  
frames_per_image = max(1, frames_total // len(images))  
frames_per_image *= 2    
total_needed_frames = frames_total  
frames_generated = 0  
  
for img_file in images:  
    img_base = Image.open(img_file)  
    img_base = crop_to_frame(img_base, WIDTH, HEIGHT)  
    for f in range(frames_per_image):  
        zoom = 1 + 0.05 * np.sin(np.pi * f / frames_per_image)  
        w,h = int(WIDTH*zoom), int(HEIGHT*zoom)  
        img = img_base.resize((w,h))  
        left = (w-WIDTH)//2  
        top = (h-HEIGHT)//2  
        img_cropped = img.crop((left,top,left+WIDTH,top+HEIGHT)).convert("RGB")  
        frame = cv2.cvtColor(np.array(img_cropped), cv2.COLOR_RGB2BGR)  
        video.write(frame)  
        frames_generated += 1  
        if frames_generated >= total_needed_frames:  
            break  
    if frames_generated >= total_needed_frames:  
        break  
  
video.release()  
print("✅ Video created!")  
  
# -----------------------------  
# Step 5: Add Background Music  
# -----------------------------  
print("🎵 Adding background music...")  
bgm = AudioSegment.from_file(BGM_PATH) - 2  
if len(bgm) < len(voiceover): bgm = bgm * (len(voiceover)//len(bgm)+1)  
bgm = bgm[:len(voiceover)]  
final_audio = voiceover.overlay(bgm)  
final_audio.export(AUDIO_FILENAME, format="mp3")  
print("✅ Background music added!")  
  
# -----------------------------  
# Step 6: Merge Video + Audio  
# -----------------------------  
print("🔀 Merging video + audio...")  
subprocess.run([  
    "ffmpeg","-y","-i",VIDEO_FILENAME,"-i",AUDIO_FILENAME,  
    "-c:v","copy","-c:a","aac",FINAL_FILENAME  
], check=True)  
print("✅ Final video ready!")  
  
# -----------------------------  
# Step 7: Upload to YouTube  
# -----------------------------  
print("📤 Uploading to YouTube...")  
CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]  
CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]  
REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]  
  
creds = Credentials(None, refresh_token=REFRESH_TOKEN,  
                    token_uri="https://oauth2.googleapis.com/token",  
                    client_id=CLIENT_ID, client_secret=CLIENT_SECRET)  
creds.refresh(google.auth.transport.requests.Request())  
youtube = build("youtube","v3",credentials=creds)  
  
safe_description = (  
    f"Life of {topic} ❤️❤️❤️❤️ "  
    f"इस शॉर्ट वीडियो में आप {topic} के जीवन, संघर्ष और योगदान के बारे में जानेंगे।\n\n"  
    "#Shorts #Motivation #History"  
)  
tags = [topic,"जीवनी","Motivation","Success","Inspiration","India","History",  
        "Biography","Life Story","Leadership","Quotes","Legacy","Famous People",  
        "Education","Struggle","Shorts","Hindi","ज्ञान","Learning","Wisdom"]  
  
request = youtube.videos().insert(  
    part="snippet,status",  
    body={  
        "snippet":{  
            "title":f"Life of {topic} ❤️❤️❤️❤️ #Shorts",  
            "description":safe_description[:4500],  
            "tags":tags,  
            "categoryId":"22"  
        },  
        "status":{"privacyStatus":"public"}  
    },  
    media_body=FINAL_FILENAME  
)  
  
response = request.execute()  
print(f"✅ Upload complete! Video: https://www.youtube.com/watch?v={response['id']}")  
  
# -----------------------------  
# -----------------------------  
# Step 8: Mark topic as used  
# -----------------------------  
def mark_topic_as_used(topic):  
    """Append topic to used.txt safely."""  
    try:  
        # Ensure the file exists  
        if not os.path.exists(USED_FILE):  
            with open(USED_FILE, "w", encoding="utf-8") as f:  
                pass  # create empty file  
  
        # Read current used topics to avoid duplicates  
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
  
# Call Step 8 after video generation and upload  
mark_topic_as_used(topic)
