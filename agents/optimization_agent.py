import json
import logging
from datetime import datetime, timedelta

from openai import OpenAI
from analytix import Client
from analytix.reports import Report

from utils.config import Config
from utils.optimization_rules import load_rules, save_rules

logger = logging.getLogger(__name__)


class OptimizationAgent:
    def __init__(self):
        self.analytix_client_id = Config.ANALYTIX_CLIENT_ID
        self.analytix_client_secret = Config.ANALYTIX_CLIENT_SECRET
        self.openrouter_key = Config.OPENROUTER_API_KEY
        self.model = Config.OPENROUTER_MODEL
        self.rules_path = Config.OPTIMIZATION_RULES_PATH
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_key,
        )

    def fetch_analytics(self) -> list[dict]:
        if not self.analytix_client_id or not self.analytix_client_secret:
            logger.warning("Analytix credentials not configured, using mock data")
            return self._mock_analytics_data()

        client = Client(
            client_id=self.analytix_client_id,
            client_secret=self.analytix_client_secret,
        )

        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        report: Report = client.fetch_report(
            dimensions=["video", "day"],
            metrics=["views", "averageViewDuration", "likes", "comments", "shares"],
            start_date=seven_days_ago,
            end_date=today,
        )

        videos = []
        for row in report.to_dict():
            videos.append({
                "video_id": row.get("video", ""),
                "title": row.get("videoTitle", ""),
                "views": row.get("views", 0),
                "avg_duration": row.get("averageViewDuration", 0),
                "likes": row.get("likes", 0),
                "comments": row.get("comments", 0),
                "shares": row.get("shares", 0),
                "date": row.get("day", ""),
            })
        return videos

    def _mock_analytics_data(self) -> list[dict]:
        return [
            {
                "video_id": "mock1",
                "title": "The Life of Harriet Tubman",
                "views": 15200,
                "avg_duration": 45,
                "likes": 1200,
                "comments": 85,
                "shares": 340,
                "date": (datetime.now() - timedelta(days=1)).isoformat(),
            },
            {
                "video_id": "mock2",
                "title": "The Harlem Renaissance Explained",
                "views": 8900,
                "avg_duration": 52,
                "likes": 670,
                "comments": 42,
                "shares": 210,
                "date": (datetime.now() - timedelta(days=3)).isoformat(),
            },
            {
                "video_id": "mock3",
                "title": "Rosa Parks: Beyond the Bus",
                "views": 23400,
                "avg_duration": 61,
                "likes": 1900,
                "comments": 156,
                "shares": 520,
                "date": (datetime.now() - timedelta(days=5)).isoformat(),
            },
            {
                "video_id": "mock4",
                "title": "Black Inventors Who Changed the World",
                "views": 31000,
                "avg_duration": 58,
                "likes": 2400,
                "comments": 203,
                "shares": 780,
                "date": (datetime.now() - timedelta(days=6)).isoformat(),
            },
            {
                "video_id": "mock5",
                "title": "The Underground Railroad Stories",
                "views": 6700,
                "avg_duration": 38,
                "likes": 450,
                "comments": 28,
                "shares": 95,
                "date": (datetime.now() - timedelta(days=7)).isoformat(),
            },
        ]

    def analyze_and_generate_rules(self):
        videos = self.fetch_analytics()
        if not videos:
            logger.warning("No video analytics data to analyze")
            return

        videos_sorted = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)
        top_videos = videos_sorted[:3]
        low_videos = videos_sorted[-2:]

        prompt = (
            "You are a YouTube optimization analyst for a Black History educational channel.\n\n"
            "Analyze the following video performance data and extract optimization rules.\n\n"
            "TOP PERFORMING VIDEOS:\n" +
            "\n".join(
                f"- '{v['title']}': {v['views']} views, {v['avg_duration']}s avg duration, "
                f"{v['likes']} likes, {v['comments']} comments"
                for v in top_videos
            ) +
            "\n\nLOW PERFORMING VIDEOS:\n" +
            "\n".join(
                f"- '{v['title']}': {v['views']} views, {v['avg_duration']}s avg duration"
                for v in low_videos
            ) +
            "\n\nOutput a JSON object with this schema:\n"
            '{\n'
            '  "rules": [\n'
            '    {\n'
            '      "category": "figures|cultural|economic|inventions|movements|military|history|general",\n'
            '      "rule": "string describing the actionable rule",\n'
            '      "source_video": "title of the video this rule is derived from",\n'
            '      "rule_type": "hook_style|thumbnail_element|posting_time|topic_angle|length|call_to_action"\n'
            '    }\n'
            '  ]\n'
            '}\n\n'
            "Return ONLY valid JSON. No markdown, no extra text."
        )

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500,
        )

        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
            if content.endswith("```"):
                content = content[:-3]

        try:
            new_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM rules output: %s", e)

            new_data = {
                "rules": [
                    {
                        "category": "general",
                        "rule": f"High engagement detected for videos about {top_videos[0]['title']} - similar topic angle recommended",
                        "source_video": top_videos[0]["title"],
                        "rule_type": "topic_angle",
                    }
                ]
            }

        rules = load_rules(self.rules_path)
        rules["rules"] = new_data.get("rules", [])
        rules["last_updated"] = datetime.now().isoformat()
        rules["version"] = rules.get("version", 1) + 1
        save_rules(self.rules_path, rules)

        logger.info("Generated %d optimization rules", len(rules["rules"]))
        return rules
