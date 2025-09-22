import os
from moviepy.editor import TextClip, CompositeVideoClip
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==============================
# Config
# ==============================
TEXT = "Hello YouTube Shorts! 🚀\nThis is an automated test upload."
VIDEO_FILE = "output.mp4"

# ==============================
# Step 1: Generate Video
# ==============================
print("🎬 Generating video...")

txt_clip = TextClip(
    TEXT,
    fontsize=40,
    color="white",
    size=(720, 480),
    method="caption",
    font="DejaVu-Sans"
).set_duration(10)

video = CompositeVideoClip([txt_clip])
video.write_videofile(VIDEO_FILE, fps=24)

print("✅ Video generated:", VIDEO_FILE)

# ==============================
# Step 2: Upload to YouTube
# ==============================
print("📤 Uploading to YouTube...")

# Load credentials from GitHub Secrets (set in workflow)
creds = Credentials(
    None,
    refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.getenv("YOUTUBE_CLIENT_ID"),
    client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)

# Refresh token if needed
request = google.auth.transport.requests.Request()
creds.refresh(request)

youtube = build("youtube", "v3", credentials=creds)

request_body = {
    "snippet": {
        "categoryId": "22",  # People & Blogs
        "title": "🚀 Automated YouTube Short Test",
        "description": "This short was uploaded automatically using GitHub Actions + Python!",
        "tags": ["automation", "shorts", "python"]
    },
    "status": {
        "privacyStatus": "private"  # change to "public" later
    }
}

media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/mp4")
upload = youtube.videos().insert(
    part="snippet,status",
    body=request_body,
    media_body=media_file
)

response = upload.execute()
print("✅ Upload successful! Video ID:", response["id"])    token_uri='https://oauth2.googleapis.com/token'
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
