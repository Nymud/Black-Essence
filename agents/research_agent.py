import logging
import re
import urllib.parse

import httpx
from openai import OpenAI

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self):
        self.brave_api_key = Config.BRAVE_API_KEY
        self.openrouter_key = Config.OPENROUTER_API_KEY
        self.openrouter_model = Config.OPENROUTER_MODEL

    def _brave_search(self, query: str, count: int = 10) -> list[dict]:
        if not self.brave_api_key:
            raise RuntimeError("Brave API key not configured")

        encoded = urllib.parse.quote(query)
        url = f"https://api.search.brave.com/res/v1/web/search?q={encoded}&count={count}"

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.brave_api_key,
        }

        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", []):
            url_field = item.get("url", "")
            domain_priority = 0
            if re.search(r"\.edu\b", url_field):
                domain_priority = 2
            elif re.search(r"\.org\b", url_field):
                domain_priority = 1

            results.append({
                "title": item.get("title", ""),
                "url": url_field,
                "description": item.get("description", ""),
                "domain_priority": domain_priority,
            })

        results.sort(key=lambda x: x["domain_priority"], reverse=True)
        return results

    def _gemini_fallback(self, query: str) -> list[dict]:
        if not self.openrouter_key:
            raise RuntimeError("OpenRouter key not configured for fallback")

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_key,
        )

        prompt = (
            f"You are a research assistant for a Black History educational channel. "
            f"Research the topic: '{query}'. "
            f"Return a JSON array of objects with 'title', 'url', and 'description' fields. "
            f"Prioritize .edu and .org sources. Return at least 5 results. JSON only, no markdown."
        )

        resp = client.chat.completions.create(
            model=self.openrouter_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        import json
        results = json.loads(content)
        for r in results:
            url = r.get("url", "")
            r["domain_priority"] = 2 if re.search(r"\.edu", url) else (1 if re.search(r"\.org", url) else 0)
        return results

    def research(self, topic: str) -> list[dict]:
        chain = FallbackChain("ResearchAgent")
        chain.add_handler(self._brave_search, "BraveSearch")
        chain.add_handler(self._gemini_fallback, "GeminiFallback")
        return chain.execute(topic)
