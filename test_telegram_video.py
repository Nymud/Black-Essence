import asyncio, sys, logging, os
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from bot.telegram_bot import TelegramApprovalBot

from utils.csv_schedule import get_topic_for_slot
from datetime import date
_entry = get_topic_for_slot("schedule.csv", date.today(), "10:00")
topic = _entry.topic if _entry else "Black History Spotlight"
video_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_horizontal.mp4")
thumb_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_thumb.png")

async def main():
    bot = TelegramApprovalBot()
    await bot.start()
    
    print(f"Sending video ({os.path.getsize(video_path)/1024/1024:.1f}MB)...")
    with open(video_path, "rb") as f:
        await bot.bot.send_video(
            chat_id=bot.admin_chat_id,
            video=f,
            caption=f"Test video: {topic}",
            read_timeout=120,
            write_timeout=120,
            connect_timeout=60,
        )
    print("Video sent! Check Telegram")

if __name__ == "__main__":
    asyncio.run(main())
