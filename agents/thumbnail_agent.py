import base64
import json
import logging
import os
import tempfile
import httpx
from PIL import Image, ImageDraw, ImageFont

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class ThumbnailAgent:
    def __init__(self):
        self.hf_token = Config.HF_API_TOKEN
        self.hf_model = Config.HF_STABLE_DIFFUSION_MODEL

    def _generate_hf(self, topic: str) -> str:
        if not self.hf_token:
            raise RuntimeError("Hugging Face token not configured")

        prompt = (
            f"Thumbnail for black history educational video about {topic}, "
            f"bold colors, dramatic lighting, cinematic, text overlay space, "
            f"high contrast, 16:9, professional youtube thumbnail style"
        )

        api_url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}

        resp = httpx.post(api_url, json={"inputs": prompt}, headers=headers, timeout=120)
        resp.raise_for_status()

        out = tempfile.NamedTemporaryFile(suffix=".png", prefix="thumb_", delete=False)
        out_path = out.name
        out.close()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        logger.info("HF Stable Diffusion thumbnail saved to %s", out_path)
        return out_path

    def _generate_pil_fallback(self, topic: str) -> str:
        img = Image.new("RGB", (1280, 720), color=(10, 10, 40))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 48)
            sub_font = ImageFont.truetype("arial.ttf", 28)
        except (OSError, IOError):
            font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

        lines = []
        words = topic.split()
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if len(test) < 30:
                current = test
            else:
                lines.append(current)
                current = w
        if current:
            lines.append(current)

        y_start = 200
        for i, line in enumerate(lines[:3]):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(
                ((1280 - tw) // 2, y_start + i * 60),
                line,
                fill=(255, 215, 0),
                font=font,
            )

        bottom_text = "BLACK ESSENCE"
        bbox = draw.textbbox((0, 0), bottom_text, font=sub_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((1280 - tw) // 2, 620),
            bottom_text,
            fill=(255, 255, 255),
            font=sub_font,
        )

        out = tempfile.NamedTemporaryFile(suffix=".png", prefix="thumb_fallback_", delete=False)
        out_path = out.name
        out.close()
        img.save(out_path, "PNG")
        logger.info("PIL fallback thumbnail saved to %s", out_path)
        return out_path

    def generate_thumbnail(self, topic: str) -> str:
        chain = FallbackChain("ThumbnailAgent")
        chain.add_handler(self._generate_hf, "HuggingFace")
        chain.add_handler(self._generate_pil_fallback, "PILFallback")
        return chain.execute(topic)
