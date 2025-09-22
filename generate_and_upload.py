import os
from moviepy.editor import ColorClip, concatenate_videoclips
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.editor import AudioClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from gtts import gTTS

# -----------------------------
# CONFIG
# -----------------------------
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
ACCESS_TOKEN = os.environ.get("YOUTUBE_ACCESS_TOKEN")  # optional, auto-refresh

VIDEO_TITLE = "Test Short"
VIDEO_DESC = "This is a 10-second test short generated automatically."
VIDEO_TAGS = ["test", "short", "github-actions"]
VIDEO_FILENAME = "output.mp4"
AUDIO_FILENAME = "audio.mp3"

TEXT_TO_SPEAK = "Hello! This is a test short generated automatically by GitHub Actions."

# -----------------------------
# CREATE AUDIO
# -----------------------------
tts = gTTS(text=TEXT_TO_SPEAK, lang='en')
tts.save(AUDIO_FILENAME)

# Load audio to get duration
audio_clip = AudioFileClip(AUDIO_FILENAME)
duration = audio_clip.duration

# -----------------------------
# CREATE VIDEO
# -----------------------------
# Create simple color clip with the same duration as audio
video_clip = ColorClip(size=(720, 480), color=(0, 0, 0), duration=duration)

# Add audio
video_clip = video_clip.set_audio(audio_clip)

# Write video file
video_clip.write_videofile(VIDEO_FILENAME, fps=24, codec="libx264", audio_codec="aac")

# -----------------------------
# UPLOAD TO YOUTUBE
# -----------------------------
# Set up credentials
creds = Credentials(
    token=ACCESS_TOKEN,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build('youtube', 'v3', credentials=creds)

# Prepare upload
request_body = {
    "snippet": {
        "title": VIDEO_TITLE,
        "description": VIDEO_DESC,
        "tags": VIDEO_TAGS,
        "categoryId": "22"  # People & Blogs
    },
    "status": {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False
    }
}

media = MediaFileUpload(VIDEO_FILENAME)

request = youtube.videos().insert(
    part="snippet,status",
    body=request_body,
    media_body=media
)
response = request.execute()

print("✅ Uploaded successfully! Video ID:", response.get("id"))    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

youtube = build("youtube", "v3", credentials=creds)

title = f"Test Short {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
request_body = {
    "snippet": {
        "title": title,
        "description": "This is an auto-uploaded test short.",
        "tags": ["test", "shorts", "automation"],
        "categoryId": "22"
    },
    "status": {"privacyStatus": "unlisted"}
}

media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/*")
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()

print("✅ Uploaded successfully! Video ID:", response.get("id"))    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

youtube = build("youtube", "v3", credentials=creds)

title = f"Test Short {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
request_body = {
    "snippet": {
        "title": title,
        "description": "This is an auto-uploaded test short.",
        "tags": ["test", "shorts", "automation"],
        "categoryId": "22"
    },
    "status": {"privacyStatus": "unlisted"}
}

media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/*")
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()

print("✅ Uploaded successfully! Video ID:", response.get("id"))    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)

youtube = build("youtube", "v3", credentials=creds)

title = f"Test Short {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
request_body = {
    "snippet": {
        "title": title,
        "description": "This is an auto-uploaded test short.",
        "tags": ["test", "shorts", "automation"],
        "categoryId": "22",
    },
    "status": {"privacyStatus": "unlisted"},
}

media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/*")
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()

print("✅ Uploaded successfully! Video ID:", response.get("id"))    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)

youtube = build("youtube", "v3", credentials=creds)

title = f"Test Short {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
request_body = {
    "snippet": {
        "title": title,
        "description": "This is an auto-uploaded test short.",
        "tags": ["test", "shorts", "automation"],
        "categoryId": "22",
    },
    "status": {"privacyStatus": "unlisted"},
}

media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/*")
request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
response = request.execute()

print("✅ Uploaded successfully! Video ID:", response.get("id"))
