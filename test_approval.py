import asyncio, sys, logging, os, threading, time
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from bot.telegram_bot import TelegramApprovalBot

topic = "The Life of Harriet Tubman"
video_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_horizontal.mp4")
thumb_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_thumb.png")

if not os.path.exists(thumb_path):
    from PIL import Image
    img = Image.new("RGB", (1280, 720), (0, 0, 0))
    img.save(thumb_path)

async def main():
    bot = TelegramApprovalBot()
    await bot.start()

    poll_thread = threading.Thread(target=bot.run_polling, daemon=True)
    poll_thread.start()
    time.sleep(2)

    print("=" * 50)
    print("Sending approval request to Telegram...")
    print("Reply in Telegram with /approve <id> or /reject <id> reason")
    print("Waiting up to 90 seconds for your response...")
    print("=" * 50)

    req = await bot.request_approval(
        video_path=video_path,
        thumbnail_path=thumb_path,
        topic=topic,
        timeout=90,
    )

    print(f"\nResult: {req.status}")
    if req.feedback:
        print(f"Feedback: {req.feedback}")
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
