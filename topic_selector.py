import random
import os

TOPICS_FILE = "topics.txt"
USED_FILE = "used.txt"

def get_next_topic():
    # Load all topics
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip()]

    # Ensure used.txt exists
    if not os.path.exists(USED_FILE):
        open(USED_FILE, "w", encoding="utf-8").close()

    # Load already used topics
    with open(USED_FILE, "r", encoding="utf-8") as f:
        used = {line.strip() for line in f if line.strip()}

    # Get unused topics
    unused = [t for t in topics if t not in used]

    if not unused:
        print("🎉 All topics have been used! Reset used.txt to start again.")
        return None

    # Randomly choose a topic
    topic = random.choice(unused)

    # Save selected topic into used.txt
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")

    return topic
