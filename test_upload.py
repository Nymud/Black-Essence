import sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from agents.publishing_agent import PublishingAgent

topic = "The Life of Harriet Tubman"
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
