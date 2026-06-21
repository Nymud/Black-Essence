"""CLI entry point for Heroku Scheduler.
Usage: python run_production.py [--topic TOPIC] [--category CATEGORY] [--slot 10:00|18:00]
If no topic given, picks from today's schedule.
"""
import sys, os, argparse, asyncio, logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from datetime import date
from agents.production_agent import ProductionResult
from agents.publishing_agent import PublishingAgent
from utils.csv_schedule import get_topic_for_slot


def get_today_topic(time_slot: str):
    csv_path = os.environ.get("SCHEDULE_CSV", "schedule.csv")
    entry = get_topic_for_slot(csv_path, date.today(), time_slot)
    if entry:
        return entry.topic, entry.category
    return f"Black History Spotlight - {date.today().strftime('%B %d')}", "general"


def main():
    parser = argparse.ArgumentParser(description="Run a single production cycle")
    parser.add_argument("--topic", type=str, default=None, help="Override topic")
    parser.add_argument("--category", type=str, default=None, help="Override category")
    parser.add_argument("--slot", type=str, default=None, help="Time slot: 10:00 or 18:00")
    args = parser.parse_args()

    if args.topic:
        topic = args.topic
        category = args.category or "general"
    elif args.slot:
        topic, category = get_today_topic(args.slot)
    else:
        # Default: pick 10:00 slot topic
        topic, category = get_today_topic("10:00")

    print(f"\n{'='*50}")
    print(f"Production Cycle")
    print(f"Topic: {topic}")
    print(f"Category: {category}")
    print(f"{'='*50}\n")

    from agents.production_agent import ProductionAgent
    try:
        agent = ProductionAgent(telegram_bot=None)
        result = agent.produce(topic, category)
        print(f"\nVideo: {result.video_path}")
        print(f"Size: {os.path.getsize(result.video_path) / 1024 / 1024:.1f} MB")

        print(f"\nPublishing...")
        publisher = PublishingAgent()
        pub = publisher.publish_all(
            video_path=result.video_path,
            vertical_path=result.vertical_path,
            title=f"{topic} | Black Essence",
            description=(
                f"Discover the inspiring story of {topic}.\n"
                f"Part of our Black History educational series.\n\n"
                f"#BlackHistory #Education #Shorts #BlackExcellence"
            ),
            thumbnail_path=result.thumbnail_path,
        )
        if pub.youtube_url:
            print(f"YouTube: {pub.youtube_url}")
        print(f"\nDONE")
    except Exception as e:
        logging.error("Production failed: %s", e, exc_info=True)
        print(f"\nFAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
