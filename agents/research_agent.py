import json
import logging
import re

from openai import OpenAI

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self):
        self.openrouter_key = Config.OPENROUTER_API_KEY
        self.openrouter_model = Config.OPENROUTER_MODEL

    def _duckduckgo_search(self, query: str) -> list[dict]:
        from duckduckgo_search import DDGS
        results = []
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=10):
            url_field = r.get("href", "")
            domain_priority = 2 if re.search(r"\.edu", url_field) else (
                1 if re.search(r"\.org", url_field) else 0
            )
            results.append({
                "title": r.get("title", ""),
                "url": url_field,
                "description": r.get("body", ""),
                "domain_priority": domain_priority,
            })
        results.sort(key=lambda x: x["domain_priority"], reverse=True)
        if not results:
            raise RuntimeError(f"No DuckDuckGo results for '{query}'")
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

        results = json.loads(content)
        for r in results:
            url = r.get("url", "")
            r["domain_priority"] = 2 if re.search(r"\.edu", url) else (1 if re.search(r"\.org", url) else 0)
        return results

    def research(self, topic: str) -> list[dict]:
        chain = FallbackChain("ResearchAgent")
        chain.add_handler(self._duckduckgo_search, "DuckDuckGo")
        chain.add_handler(self._gemini_fallback, "GeminiFallback")
        return chain.execute(topic)
