"""Entry point.
- On Heroku (DYNO env var set): Flask web + APScheduler + Telegram notifications
- Locally: full orchestrator with Telegram bot polling
"""
import os, sys, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

if os.environ.get("DYNO"):
    from flask import Flask
    app = Flask(__name__)

    @app.route("/")
    def health():
        return "Black Essence OK", 200

    @app.route("/run/<slot>")
    def trigger(slot):
        """Manually trigger a production cycle via HTTP."""
        from threading import Thread
        t = Thread(target=run_production_cycle, args=[slot])
        t.start()
        return f"Production cycle started for {slot}", 200

    import threading
    import httpx
    from apscheduler.schedulers.background import BackgroundScheduler
    from datetime import date
    from utils.csv_schedule import get_topic_for_slot
    from agents.production_agent import ProductionAgent
    from agents.publishing_agent import PublishingAgent
    from utils.config import Config

    def send_telegram(text):
        """Send a message to the admin chat via Telegram Bot API (no polling needed)."""
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_ADMIN_CHAT_ID
        if not token or not chat_id:
            return
        try:
            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            logging.error("Telegram send failed: %s", e)

    def run_production_cycle(time_slot):
        csv_path = os.environ.get("SCHEDULE_CSV", "schedule.csv")
        entry = get_topic_for_slot(csv_path, date.today(), time_slot)
        if not entry:
            logging.info("No topic for %s, skipping", time_slot)
            return

        send_telegram(f"🎬 <b>Starting production</b>\nTopic: {entry.topic}\nSlot: {time_slot}")

        try:
            agent = ProductionAgent(telegram_bot=None)
            result = agent.produce(entry.topic, entry.category)
            logging.info("Produced: %s -> %s", entry.topic, result.video_path)

            video_size = os.path.getsize(result.video_path) / 1024 / 1024
            send_telegram(
                f"✅ <b>Video ready for review</b>\n"
                f"Topic: {entry.topic}\n"
                f"Size: {video_size:.1f} MB\n"
                f"Duration: ~{video_size * 3:.0f}s\n\n"
                f"Reply <b>/approve</b> to publish or <b>/reject</b> to skip."
            )

            publisher = PublishingAgent()
            pub = publisher.publish_all(
                video_path=result.video_path,
                vertical_path=result.vertical_path,
                title=f"{entry.topic} | Black Essence",
                description=f"Discover the inspiring story of {entry.topic}.\n\n#BlackHistory #Education #Shorts #BlackExcellence",
                thumbnail_path=result.thumbnail_path,
            )
            if pub.youtube_url:
                send_telegram(f"📤 <b>Published!</b>\n{pub.youtube_url}")
                logging.info("YouTube: %s", pub.youtube_url)
            else:
                send_telegram("⚠️ Video produced but publishing skipped (token issue)")

        except Exception as e:
            logging.error("Production failed: %s", e, exc_info=True)
            send_telegram(f"❌ <b>Production failed</b>\nTopic: {entry.topic}\nError: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_production_cycle, "cron", hour=10, minute=0, args=["10:00"], id="prod_10am")
    scheduler.add_job(run_production_cycle, "cron", hour=18, minute=0, args=["18:00"], id="prod_6pm")
    scheduler.start()
    logging.info("Scheduler started: production at 10:00 and 18:00 UTC")

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
else:
    from orchestrator import main
    main()
