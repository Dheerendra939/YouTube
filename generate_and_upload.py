import os, random, requests, json, re, textwrap, subprocess, math
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import texttospeech
import google.auth.transport.requests

# ======================
# CONFIG
# ======================
VIDEO_LENGTH = 55
IMAGE_COUNT = 10
AUDIO_FILE = "voice.mp3"
OUTPUT_FILE = "final.mp4"

# ======================
# GEMINI HELPERS
# ======================
def pick_topic():
    topics = [
        "प्रसिद्ध व्यक्तित्व", "विज्ञान की खोजें",
        "प्रेरणादायक जीवन कथाएँ", "ऐतिहासिक घटनाएँ",
        "दुनिया के रोचक तथ्य", "प्रेरक विचार"
    ]
    base_topic = random.choice(topics)
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")
    resp = model.generate_content(
        f"Suggest one engaging Hindi topic (3-4 words) for a 1-minute YouTube Short about {base_topic}."
    )
    return resp.text.strip()

def generate_script(topic):
    model = genai.GenerativeModel("gemini-pro")
    resp = model.generate_content(
        f"Write an engaging 55-second motivational short script in Hindi about {topic}. "
        "Keep it simple, inspiring, and suitable for narration."
    )
    return resp.text.strip()

def generate_metadata(topic, script):
    model = genai.GenerativeModel("gemini-pro")
    prompt = (
        f"Generate YouTube metadata for a Hindi Shorts video.\n"
        f"Topic: {topic}\n\n"
        f"Script: {script}\n\n"
        f"Return JSON with fields: title, description, tags (20 Hindi/English mix, trending, relevant)."
    )
    resp = model.generate_content(prompt)
    try:
        data = json.loads(resp.text)
    except:
        # fallback if Gemini outputs plain text
        data = {
            "title": f"{topic} | प्रेरणादायक कहानी #Shorts",
            "description": script[:4500] + "\n\n#Shorts #Motivation #Inspiration",
            "tags": [
                "Motivation", "Shorts", "Inspiration", "Life Lessons",
                "Hindi Motivation", "History", "Personality", "Education",
                "Learning", "Success", "Struggle", "Motivational Video",
                "Hindi Shorts", "Knowledge", "Wisdom", "Great Leaders",
                "Facts", "Biography", "Motivational Shorts", "Inspiring Stories"
            ]
        }
    return data

# ======================
# PEXELS IMAGES
# ======================
def fetch_images(query):
    headers = {"Authorization": os.environ["PEXELS_API_KEY"]}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={IMAGE_COUNT}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("❌ Pexels API error:", r.text)
        return []
    data = r.json()
    images = [photo["src"]["large"] for photo in data.get("photos", [])]
    while len(images) < IMAGE_COUNT and len(images) > 0:
        images.append(random.choice(images))
    return images

# ======================
# GOOGLE TTS
# ======================
def generate_audio(text):
    creds_info = json.loads(os.environ["TTS"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    tts_client = texttospeech.TextToSpeechClient(credentials=creds)
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.MALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, pitch=-6)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(AUDIO_FILE, "wb") as f:
        f.write(response.audio_content)
    print("✅ Audio generated!")

# ======================
# VIDEO CREATION
# ======================
def create_video(images, text, audio_file, output_file):
    per_image = VIDEO_LENGTH / len(images)
    wrapped = textwrap.fill(text, width=40)
    lines = wrapped.split("\n")
    step = math.floor(VIDEO_LENGTH / len(lines))
    caption_file = "captions.srt"
    with open(caption_file, "w", encoding="utf-8") as f:
        t = 0
        for i, line in enumerate(lines, 1):
            f.write(f"{i}\n")
            f.write(f"00:00:{t:02d},000 --> 00:00:{t+step:02d},000\n")
            f.write(line + "\n\n")
            t += step

    local_images = []
    for i, url in enumerate(images):
        fname = f"img_{i}.jpg"
        r = requests.get(url, timeout=15)
        with open(fname, "wb") as f:
            f.write(r.content)
        local_images.append(fname)

    inputs = []
    for img in local_images:
        inputs.extend(["-loop", "1", "-t", str(per_image), "-i", img])

    ffmpeg_cmd = [
        "ffmpeg", *inputs,
        "-i", audio_file,
        "-filter_complex",
        f"concat=n={len(local_images)}:v=1:a=0,subtitles={caption_file}",
        "-c:v", "libx264", "-t", str(VIDEO_LENGTH),
        "-pix_fmt", "yuv420p", "-shortest", output_file, "-y"
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print("✅ Video created!")

# ======================
# YOUTUBE UPLOAD
# ======================
def upload_to_youtube(meta):
    from google.oauth2.credentials import Credentials
    CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
    CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
    REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]

    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    creds.refresh(google.auth.transport.requests.Request())
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=OUTPUT_FILE
    )
    response = request.execute()
    print(f"✅ Upload complete! https://www.youtube.com/watch?v={response['id']}")

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    topic = pick_topic()
    print(f"🎯 Topic: {topic}")

    script = generate_script(topic)
    print("📖 Script ready!")

    meta = generate_metadata(topic, script)
    print("📝 Metadata generated!")

    images = fetch_images(topic)
    if not images:
        raise Exception("❌ No images from Pexels.")

    generate_audio(script)
    create_video(images, script, AUDIO_FILE, OUTPUT_FILE)
    upload_to_youtube(meta)
