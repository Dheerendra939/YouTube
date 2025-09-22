import os
import datetime
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========== Step 1: Generate 10-sec video ==========
TEXT = "Hello World! This is a test Short."
VIDEO_FILE = "output.mp4"

# Background
background = ColorClip(size=(720, 1280), color=(30, 30, 30), duration=10)

# Text
txt_clip = TextClip(
    TEXT,
    fontsize=60,
    color="white",
    size=(700, None),
    method="caption",
).set_position("center").set_duration(10)

# Final video
final = CompositeVideoClip([background, txt_clip])
final.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio=False)

# ========== Step 2: Upload to YouTube ==========
CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")

creds = Credentials(
    None,
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

print("✅ Uploaded successfully! Video ID:", response.get("id"))
