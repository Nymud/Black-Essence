import asyncio
import logging
import os
import sys
import threading
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from utils.csv_schedule import get_topic_for_slot
from utils.optimization_rules import load_rules
from agents.production_agent import ProductionAgent
from agents.publishing_agent import PublishingAgent
from agents.optimization_agent import OptimizationAgent
from bot.telegram_bot import TelegramApprovalBot, ApprovalStatus

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Orchestrator")


class Orchestrator:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.telegram_bot = TelegramApprovalBot()
        self.optimization_agent = OptimizationAgent()
        self.running = True

    async def run_production_cycle(self, time_slot_label: str):
        logger.info("=== Production cycle starting (%s) ===", time_slot_label)

        today = date.today()
        entry = get_topic_for_slot(Config.SCHEDULE_CSV, today, time_slot_label)

        if not entry:
            logger.info("No topic scheduled for %s at %s. Checking fallback.", today, time_slot_label)
            entries = get_topic_for_slot.__wrapped__ if hasattr(get_topic_for_slot, "__wrapped__") else None
            fallback_topic = f"Black History Fact - {today.strftime('%B %d, %Y')}"
            entry = type("Entry", (), {
                "topic": fallback_topic,
                "category": "general",
                "date": today,
                "time_slot": time_slot_label,
            })
            logger.info("Using fallback topic: %s", fallback_topic)

        logger.info("Producing video for topic: %s (category: %s)", entry.topic, entry.category)

        try:
            production = ProductionAgent(telegram_bot=self.telegram_bot)
            result = production.produce(entry.topic, entry.category)

            logger.info("Requesting approval...")
            approval = await self.telegram_bot.request_approval(
                video_path=result.video_path,
                thumbnail_path=result.thumbnail_path,
                topic=entry.topic,
            )

            if approval.status == ApprovalStatus.REJECTED:
                logger.warning("Video rejected: %s. Feedback: %s", entry.topic, approval.feedback)
                return

            logger.info("Video approved. Publishing...")
            publisher = PublishingAgent()
            pub_result = publisher.publish_all(
                video_path=result.video_path,
                vertical_path=result.vertical_path,
                title=f"{entry.topic} | Black Essence",
                description=(
                    f"Discover the inspiring story of {entry.topic}. "
                    f"Part of our Black History educational series.\n\n"
                    f"#BlackHistory #Education #Shorts #BlackExcellence"
                ),
                thumbnail_path=result.thumbnail_path,
            )

            if pub_result.youtube_url:
                logger.info("Published to YouTube: %s", pub_result.youtube_url)
            if pub_result.tiktok_url:
                logger.info("Published to TikTok: %s", pub_result.tiktok_url)
            if pub_result.instagram_url:
                logger.info("Published to Instagram: %s", pub_result.instagram_url)

            logger.info("=== Production cycle completed (%s) ===", time_slot_label)

        except Exception as e:
            logger.critical("Production cycle failed: %s", e)
            try:
                await self.telegram_bot.send_alert(f"Production cycle failed: {e}")
            except Exception:
                logger.error("Failed to send alert")

    async def run_optimization_cycle(self):
        logger.info("=== Optimization cycle starting ===")
        try:
            rules = self.optimization_agent.analyze_and_generate_rules()
            logger.info("Optimization complete: %d rules generated", len(rules.get("rules", [])))
            await self.telegram_bot.send_alert(
                f"Optimization cycle complete. {len(rules.get('rules', []))} rules generated."
            )
        except Exception as e:
            logger.error("Optimization cycle failed: %s", e)
            try:
                await self.telegram_bot.send_alert(f"Optimization cycle failed: {e}")
            except Exception:
                pass

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)

    def start(self):
        logger.info("Starting Black Essence Orchestrator...")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.telegram_bot.start())
        finally:
            loop.close()

        bot_thread = threading.Thread(target=self.telegram_bot.run_polling, daemon=True)
        bot_thread.start()
        logger.info("Telegram bot polling thread started")

        self.scheduler.add_job(
            self._run_async,
            "cron",
            hour=10,
            minute=0,
            args=[self.run_production_cycle("10:00")],
            id="production_10am",
        )
        self.scheduler.add_job(
            self._run_async,
            "cron",
            hour=18,
            minute=0,
            args=[self.run_production_cycle("18:00")],
            id="production_6pm",
        )
        self.scheduler.add_job(
            self._run_async,
            "cron",
            day_of_week="sun",
            hour=8,
            minute=0,
            args=[self.run_optimization_cycle()],
            id="optimization_sunday",
        )

        self.scheduler.start()
        logger.info("Scheduler started. Jobs: production at 10:00, 18:00 daily; optimization Sunday 08:00")

        try:
            import time
            while self.running:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
            self.scheduler.shutdown(wait=False)


def main():
    orch = Orchestrator()
    orch.start()


if __name__ == "__main__":
    main()
