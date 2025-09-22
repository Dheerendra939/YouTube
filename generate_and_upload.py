import os
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, concatenate_videoclips
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === CONFIG ===
TEXT = "This is a test short generated automatically!"
DURATION = 10
VIDEO_FILE = "output.mp4"

# === Create video ===
def make_video():
    # Background color
    bg = ColorClip(size=(720, 1280), color=(0, 0, 0), duration=DURATION)

    # Text in center
    txt_clip = TextClip(
        TEXT,
        fontsize=60,
        color="white",
        size=(700, None),
        method="caption",
    ).set_position("center").set_duration(DURATION)

    final = CompositeVideoClip([bg, txt_clip])
    final.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio=False)

# === Upload to YouTube ===
def upload_to_youtube():
    creds = Credentials(
        None,
        refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("YOUTUBE_CLIENT_ID"),
        client_secret=os.getenv("YOUTUBE_CLIENT_SECRET"),
    )

    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": "Test Auto Short",
            "description": "Uploaded automatically using GitHub Actions 🚀",
            "tags": ["AI", "automation", "shorts"],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "private"  # change to "public" when ready
        },
    }

    media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/*")

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading... {int(status.progress() * 100)}%")

    print("✅ Upload complete! Video ID:", response.get("id"))

if __name__ == "__main__":
    make_video()
    upload_to_youtube()
