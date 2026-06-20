import csv
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class ScheduleEntry:
    def __init__(self, date_str: str, topic: str, category: str, time_slot: str):
        self.date = date.fromisoformat(date_str)
        self.topic = topic.strip()
        self.category = category.strip()
        self.time_slot = time_slot.strip()

    def __repr__(self):
        return f"ScheduleEntry({self.date}, {self.topic}, {self.category}, {self.time_slot})"


def load_schedule(csv_path: str) -> list[ScheduleEntry]:
    entries = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(ScheduleEntry(
                    date_str=row["date"],
                    topic=row["topic"],
                    category=row["category"],
                    time_slot=row["time_slot"],
                ))
    except FileNotFoundError:
        logger.error("Schedule CSV not found at %s", csv_path)
        return []
    except Exception as e:
        logger.error("Failed to load schedule: %s", e)
        return []
    return entries


def get_topic_for_slot(csv_path: str, target_date: date, target_time: str) -> Optional[ScheduleEntry]:
    entries = load_schedule(csv_path)
    for entry in entries:
        if entry.date == target_date and entry.time_slot == target_time:
            return entry
    logger.info("No topic found for %s at %s", target_date, target_time)
    return None
