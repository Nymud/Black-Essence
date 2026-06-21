"""Manual production cycle trigger"""
import sys, os, asyncio, logging
sys.path.insert(0, r"C:\Users\hp\Documents\Black Essence")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from agents.production_agent import ProductionAgent
from agents.publishing_agent import PublishingAgent

topic = "The Life of Harriet Tubman"
category = "figures"

print(f"\n=== MANUAL PRODUCTION CYCLE ===")
print(f"Topic: {topic}")
print(f"Category: {category}\n")

try:
    production = ProductionAgent(telegram_bot=None)
    result = production.produce(topic, category)
    
    print(f"\n=== PRODUCTION COMPLETE ===")
    print(f"Video: {result.video_path}")
    print(f"Vertical: {result.vertical_path}")
    print(f"Thumbnail: {result.thumbnail_path}")
    
    # Publish
    print(f"\n=== PUBLISHING ===")
    publisher = PublishingAgent()
    pub_result = publisher.publish_all(
        video_path=result.video_path,
        vertical_path=result.vertical_path,
        title=f"{topic} | Black Essence",
        description=(
            f"Discover the inspiring story of {topic}. "
            f"Part of our Black History educational series.\n\n"
            f"#BlackHistory #Education #Shorts #BlackExcellence"
        ),
        thumbnail_path=result.thumbnail_path,
    )
    
    if pub_result.youtube_url:
        print(f"YouTube: {pub_result.youtube_url}")
    
    print(f"\n=== ALL DONE ===")

except Exception as e:
    print(f"\n=== FAILED ===")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
