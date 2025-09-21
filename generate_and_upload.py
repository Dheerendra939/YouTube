import os
from gtts import gTTS
from moviepy.editor import TextClip, CompositeVideoClip, AudioFileClip
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# ---------- CONFIG ----------
VIDEO_FILE = "short.mp4"
AUDIO_FILE = "short.mp3"
TEXT = "Albert Einstein developed the theory of relativity."
DURATION = 10  # 10 seconds

# ---------- Step 1: Generate audio ----------
tts = gTTS(text=TEXT, lang='en')
tts.save(AUDIO_FILE)

# ---------- Step 2: Create video ----------
txt_clip = TextClip(txt=TEXT, fontsize=40, color='white', size=(720, 480))
txt_clip = txt_clip.set_duration(DURATION)

audio_clip = AudioFileClip(AUDIO_FILE)
video = txt_clip.set_audio(audio_clip)

video.write_videofile(VIDEO_FILE, fps=24)

# ---------- Step 3: Upload to YouTube ----------
CLIENT_ID = os.environ['YOUTUBE_CLIENT_ID']
CLIENT_SECRET = os.environ['YOUTUBE_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YOUTUBE_REFRESH_TOKEN']

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri='https://oauth2.googleapis.com/token'
)

youtube = build('youtube', 'v3', credentials=creds)

media = MediaFileUpload(VIDEO_FILE)
request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "10 Second Biography Short",
            "description": "Testing AI short upload",
            "tags": ["short", "AI", "test"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    },
    media_body=media
)
response = request.execute()
print("✅ Uploaded video ID:", response['id'])
