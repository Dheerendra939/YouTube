import os
import time
import random
import subprocess
import requests
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from pydub import AudioSegment

# -------------------------------
# Gemini Setup
# -------------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_bio(topic):
    prompt = f"""
    Write a 55-second engaging biography of {topic} in Hindi.
    Start with a SHOCKING or SURPRISING 1-line HOOK to grab attention.
    Then continue the biography in a motivational storytelling style.
    Keep it crisp, emotional, and inspiring.
    Do not exceed 120 words.
    """
    response = genai.GenerativeModel("gemini-pro").generate_content(prompt)
    return response.text.strip()

def generate_title(topic):
    prompt = f"""
    Create a highly clickable YouTube Shorts title in Hindi for the biography of {topic}.
    Keep it under 55 characters, include curiosity, and add | #Shorts at the end.
    """
    response = genai.GenerativeModel("gemini-pro").generate_content(prompt)
    return response.text.strip()

def generate_description(topic):
    prompt = f"""
    Write a 2-line engaging YouTube description in Hindi for the biography of {topic}.
    End with 5-6 trending hashtags related to biography, shorts, motivation, and inspiration.
    """
    response = genai.GenerativeModel("gemini-pro").generate_content(prompt)
    return response.text.strip()

# -------------------------------
# Fetch images using Pexels API
# -------------------------------
def fetch_images(topic, num=10):
    headers = {"Authorization": os.getenv("PEXELS_API_KEY")}
    url = f"https://api.pexels.com/v1/search?query={topic}&per_page={num}"
    r = requests.get(url, headers=headers)
    data = r.json()
    image_files = []
    os.makedirs("images", exist_ok=True)
    for i, photo in enumerate(data.get("photos", [])):
        img_url = photo["src"]["large"]
        img_data = requests.get(img_url).content
        filename = f"images/{topic}_{i}.jpg"
        with open(filename, "wb") as f:
            f.write(img_data)
        image_files.append(filename)
    return image_files

# -------------------------------
# Generate voiceover with Google TTS
# -------------------------------
def generate_voiceover(text, filename="audio.mp3"):
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(filename, "wb") as out:
        out.write(response.audio_content)
    return filename

# -------------------------------
# Create video with images + narration
# -------------------------------
def create_video(images, narration, output="video.mp4"):
    audio = AudioSegment.from_file(narration)
    audio_length = audio.duration_seconds
    duration_per_image = audio_length / len(images)

    filters = []
    for i, img in enumerate(images):
        filters.append(f"[{i}:v]scale=1080:1920,setsar=1[v{i}]")

    concat_inputs = "".join([f"[v{i}]" for i in range(len(images))])
    filter_complex = "".join(filters) + f"{concat_inputs}concat=n={len(images)}:v=1:a=0,format=yuv420p[v]"

    cmd = [
        "ffmpeg", "-y",
    ]
    for img in images:
        cmd += ["-loop", "1", "-t", str(duration_per_image), "-i", img]
    cmd += [
        "-i", narration,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", f"{len(images)}:a",
        "-shortest", output
    ]
    subprocess.run(cmd, check=True)
    return output

# -------------------------------
# Add background music
# -------------------------------
def add_background_music(video, music="bg.mp3", output="final.mp4", music_volume=0.08):
    narration = AudioSegment.from_file("audio.mp3")
    bg = AudioSegment.from_file(music) - (20 - (music_volume * 100))  # adjust volume
    bg = bg[:len(narration)].fade_in(2000).fade_out(2000)
    final_audio = narration.overlay(bg)
    final_audio.export("temp_audio.mp3", format="mp3")

    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-i", "temp_audio.mp3",
        "-c:v", "copy", "-c:a", "aac", "-shortest", output
    ], check=True)
    return output

# -------------------------------
# Upload to YouTube
# -------------------------------
def upload_to_youtube(video_file, title, description):
    creds = Credentials(
        None,
        refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
        client_id=os.getenv("YOUTUBE_CLIENT_ID"),
        client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
    )
    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["Motivation", "Inspiration", "Biography", "Shorts"],
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(video_file),
    )
    response = request.execute()
    print(f"✅ Upload complete! Video: https://www.youtube.com/watch?v={response['id']}")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    topic = "Jim Lee"  # later picked randomly
    print(f"🎯 Selected topic: {topic}")

    print("📖 Generating biography...")
    bio = generate_bio(topic)

    print("🎬 Generating title & description...")
    title = generate_title(topic)
    description = generate_description(topic)

    print("🖼️ Fetching images...")
    images = fetch_images(topic, 10)

    print("🎙️ Generating voiceover...")
    narration = generate_voiceover(bio)

    print("🎬 Creating video...")
    video = create_video(images, narration)

    print("🎵 Adding background music...")
    final_video = add_background_music(video, "bg.mp3", "final_video.mp4")

    print("📤 Uploading...")
    upload_to_youtube(final_video, title, description)

    with open("used.txt", "a", encoding="utf-8") as f:
        f.write(topic + "\n")
    print(f"📝 Added '{topic}' to used.txt")
