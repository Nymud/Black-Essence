import sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from agents.publishing_agent import PublishingAgent

from utils.csv_schedule import get_topic_for_slot
from datetime import date
_entry = get_topic_for_slot("schedule.csv", date.today(), "10:00")
topic = _entry.topic if _entry else "Black History Spotlight"
video_path = f"output/{topic.replace(' ', '_')}_horizontal.mp4"
vertical_path = f"output/{topic.replace(' ', '_')}_vertical.mp4"

title = f"{topic} - Black History #shorts"
description = f"Learn about {topic}. #blackhistory #education #shorts"

agent = PublishingAgent()

# Test YouTube upload
print("Uploading to YouTube...")
url = agent.publish_youtube_shorts(video_path, title, description)
if url:
    print(f"[OK] YouTube: {url}")
else:
    print("[FAIL] YouTube upload failed")
