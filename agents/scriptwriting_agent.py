import json
import logging
import re
from datetime import datetime

from openai import OpenAI

from utils.config import Config
from utils.optimization_rules import load_rules, apply_rules_to_prompt

logger = logging.getLogger(__name__)


class ScriptwritingAgent:
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.model = Config.OPENROUTER_MODEL
        self.rules_path = Config.OPTIMIZATION_RULES_PATH
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    def _build_prompt(self, topic: str, research_data: list[dict], category: str) -> str:
        sources_text = "\n".join(
            f"- {r.get('title', '')}: {r.get('description', '')[:200]}"
            for r in research_data[:5]
        )

        base = (
            f"You are a scriptwriter for a Black History educational YouTube Shorts channel. "
            f"Write a 60-90 second NARRATIVE script about: '{topic}'.\n\n"
            f"Research Sources:\n{sources_text}\n\n"
            f"The script must:\n"
            f"1. Tell a compelling STORY with a narrative arc (beginning, middle, end)\n"
            f"2. Use a hook in the first 5 seconds to grab attention\n"
            f"3. Include [SCENE: description of visual] markers at key story moments for illustration\n"
            f"4. Be timed to read in 60-90 seconds at a moderate pace (~150 words)\n"
            f"5. End with a call to action\n"
            f"6. Use natural, conversational storytelling tone - NARRATE the story, do NOT describe what the viewer sees\n"
            f"7. NEVER say 'you see' or 'as you can see' - just tell the story\n\n"
            f"Example [SCENE] markers:\n"
            f"- [SCENE: Harriet Tubman as a young girl working in the fields]\n"
            f"- [SCENE: The underground railroad secret path through the woods]\n\n"
            f"Return ONLY the script text with SCENE markers. No commentary."
        )

        rules = load_rules(self.rules_path)
        return apply_rules_to_prompt(base, rules, category)

    def write_script(self, topic: str, research_data: list[dict], category: str = "general") -> str:
        prompt = self._build_prompt(topic, research_data, category)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )

        script = resp.choices[0].message.content.strip()
        script = re.sub(r"^```(?:markdown|text)?\s*", "", script)
        script = re.sub(r"\s*```$", "", script)
        return script

    def parse_scene_markers(self, script: str) -> list[str]:
        return re.findall(r"\[SCENE:\s*(.*?)\]", script, re.IGNORECASE)

    def estimate_duration(self, script: str) -> float:
        words = len(script.split())
        return (words / 150) * 60
