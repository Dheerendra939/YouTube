import cv2
import numpy as np
from gtts import gTTS
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ---------------------------
# 1. Video generation
# ---------------------------
WIDTH, HEIGHT = 720, 480
DURATION = 10  # seconds
FPS = 24
TEXT = "Hello! This is a test YouTube Short."

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_file = "video.mp4"
out = cv2.VideoWriter(video_file, fourcc, FPS, (WIDTH, HEIGHT))

for i in range(DURATION * FPS):
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    cv2.putText(frame, TEXT, (50, HEIGHT//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    out.write(frame)

out.release()

# ---------------------------
# 2. Text-to-speech
# ---------------------------
audio_file = "audio.mp3"
tts = gTTS(TEXT)
tts.save(audio_file)

# ---------------------------
# 3. Merge audio with video
# ---------------------------
final_file = "short_final.mp4"
os.system(f"ffmpeg -y -i {video_file} -i {audio_file} -c:v copy -c:a aac -shortest {final_file}")

# ---------------------------
# 4. Upload to YouTube
# ---------------------------
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Test YouTube Short",
            "description": "This is an automatically generated test short.",
            "tags": ["test", "short", "automation"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False
        }
    },
    media_body=MediaFileUpload(final_file)
)

response = request.execute()
print("✅ Uploaded Video ID:", response["id"])# 3. Merge audio with video
# ---------------------------
final_file = "short_final.mp4"
os.system(f"ffmpeg -y -i {video_file} -i {audio_file} -c:v copy -c:a aac -shortest {final_file}")

# ---------------------------
# 4. Upload to YouTube
# ---------------------------
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Test YouTube Short",
            "description": "This is an automatically generated test short.",
            "tags": ["test", "short", "automation"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False
        }
    },
    media_body=MediaFileUpload(final_file)
)

response = request.execute()
print("✅ Uploaded Video ID:", response["id"])
# ---------------------------
# 3. Merge audio with video
# ---------------------------
final_file = "short_final.mp4"
os.system(f"ffmpeg -y -i {video_file} -i {audio_file} -c:v copy -c:a aac -shortest {final_file}")

# ---------------------------
# 4. Upload to YouTube
# ---------------------------
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Test YouTube Short",
            "description": "This is an automatically generated test short.",
            "tags": ["test", "short", "automation"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False
        }
    },
    media_body=MediaFileUpload(final_file)
)

response = request.execute()
print("✅ Uploaded Video ID:", response["id"])# ----------------------------
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter(VIDEO_FILENAME, fourcc, FPS, (WIDTH, HEIGHT))

for i in range(FPS * DURATION):
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    # Background color
    frame[:] = (50, 50, 200)
    
    # Put text in the center
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (255, 255, 255)
    thickness = 2
    text_size = cv2.getTextSize(TEXT, font, font_scale, thickness)[0]
    text_x = (WIDTH - text_size[0]) // 2
    text_y = (HEIGHT + text_size[1]) // 2
    cv2.putText(frame, TEXT, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    video.write(frame)

video.release()

# ----------------------------
# Step 3: Combine audio + video using ffmpeg
# ----------------------------
import subprocess
final_video = "final_short.mp4"
subprocess.run([
    "ffmpeg", "-y",
    "-i", VIDEO_FILENAME,
    "-i", AUDIO_FILENAME,
    "-c:v", "copy",
    "-c:a", "aac",
    "-shortest",
    final_video
])

# ----------------------------
# Step 4: Upload to YouTube
# ----------------------------
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
creds = Credentials(
    token=ACCESS_TOKEN,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Test Short from GitHub Actions",
            "description": "This is a test Short uploaded automatically via GitHub Actions.",
            "tags": ["test", "github actions", "youtube short"],
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "private"
        }
    },
    media_body=final_video
)

response = request.execute()
print("✅ Video uploaded successfully! Video ID:", response["id"])
