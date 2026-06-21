"""Entry point.
- On Heroku (DYNO env var set): runs a lightweight web process + APScheduler
- Locally: runs the full orchestrator with Telegram bot + APScheduler
"""
import os, sys, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

if os.environ.get("DYNO"):
    # Running on Heroku — web process for health checks + scheduler for production
    from flask import Flask
    app = Flask(__name__)

    @app.route("/")
    def health():
        return "Black Essence OK", 200

    # Start APScheduler in background (no Telegram bot on Heroku)
    import threading
    from apscheduler.schedulers.background import BackgroundScheduler
    from datetime import date
    from utils.csv_schedule import get_topic_for_slot
    from agents.production_agent import ProductionAgent
    from agents.publishing_agent import PublishingAgent

    def run_production_cycle(time_slot):
        csv_path = os.environ.get("SCHEDULE_CSV", "schedule.csv")
        entry = get_topic_for_slot(csv_path, date.today(), time_slot)
        if not entry:
            logging.info("No topic for %s, skipping", time_slot)
            return
        try:
            agent = ProductionAgent(telegram_bot=None)
            result = agent.produce(entry.topic, entry.category)
            logging.info("Produced: %s -> %s", entry.topic, result.video_path)
            publisher = PublishingAgent()
            pub = publisher.publish_all(
                video_path=result.video_path,
                vertical_path=result.vertical_path,
                title=f"{entry.topic} | Black Essence",
                description=f"Discover the inspiring story of {entry.topic}.\n\n#BlackHistory #Education #Shorts",
                thumbnail_path=result.thumbnail_path,
            )
            if pub.youtube_url:
                logging.info("YouTube: %s", pub.youtube_url)
        except Exception as e:
            logging.error("Production failed: %s", e, exc_info=True)

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_production_cycle, "cron", hour=10, minute=0, args=["10:00"], id="prod_10am")
    scheduler.add_job(run_production_cycle, "cron", hour=18, minute=0, args=["18:00"], id="prod_6pm")
    scheduler.start()
    logging.info("Scheduler started: production at 10:00 and 18:00 UTC")

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
else:
    # Local dev — full orchestrator with Telegram bot
    from orchestrator import main
    main()
