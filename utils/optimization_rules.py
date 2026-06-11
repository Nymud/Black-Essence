import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RULES = {
    "version": 1,
    "rules": [],
    "last_updated": None,
}


def load_rules(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        logger.info("No optimization rules file found at %s, using defaults", path)
        return DEFAULT_RULES.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load optimization rules: %s", e)
        return DEFAULT_RULES.copy()


def save_rules(path: str, rules: dict[str, Any]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2)
        logger.info("Saved optimization rules to %s", path)
    except IOError as e:
        logger.error("Failed to save optimization rules: %s", e)


def apply_rules_to_prompt(base_prompt: str, rules: dict[str, Any], topic_category: str) -> str:
    prompt = base_prompt
    matching = [r for r in rules.get("rules", []) if r.get("category") == topic_category]
    if not matching:
        matching = rules.get("rules", [])

    if matching:
        prompt += "\n\nOptimization Rules to apply:\n"
        for rule in matching:
            prompt += f"- {rule.get('rule', '')}\n"
    return prompt
