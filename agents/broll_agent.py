import logging
import os
import tempfile
import httpx

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class BrollAgent:
    def __init__(self):
        self.hf_token = Config.HF_API_TOKEN
        self.pexels_key = Config.PEXELS_API_KEY

    def _generate_image_hf(self, query: str) -> str:
        if not self.hf_token:
            raise RuntimeError("HF token not configured")
        from huggingface_hub import InferenceClient
        client = InferenceClient(token=self.hf_token)
        prompt = f"cartoon illustration of {query}, animated storybook style, vibrant colors, educational, simple clean"
        result = client.text_to_image(
            prompt,
            model="stabilityai/stable-diffusion-xl-base-1.0",
        )
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:50]
        out = tempfile.NamedTemporaryFile(suffix=".png", prefix=f"{safe_name}_", delete=False)
        result.save(out)
        out_path = out.name
        out.close()
        logger.info("HF image for '%s' -> %s", query, out_path)
        return out_path

    def _generate_image_pollinations(self, query: str) -> str:
        prompt = f"cartoon illustration of {query}, educational, vibrant colors, simple clean style, digital art"
        url = f"https://image.pollinations.ai/prompt/{httpx.utils.quote(prompt)}?width=1280&height=720&nofeed=true"
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:50]
        out = tempfile.NamedTemporaryFile(suffix=".png", prefix=f"{safe_name}_", delete=False)
        out_path = out.name
        out.close()
        resp = httpx.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        logger.info("Pollinations image for '%s' -> %s (%d bytes)", query, out_path, len(resp.content))
        return out_path

    def get_clip(self, query: str) -> str:
        chain = FallbackChain("BrollAgent")
        if self.hf_token:
            chain.add_handler(self._generate_image_hf, "HuggingFace SDXL")
        chain.add_handler(self._generate_image_pollinations, "Pollinations")
        if self.pexels_key:
            chain.add_handler(self._search_pexels_video, "Pexels (fallback)")
        return chain.execute(query)

    def _search_pexels_video(self, query: str) -> str:
        if not self.pexels_key:
            raise RuntimeError("Pexels API key not configured")
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=1&orientation=portrait"
        headers = {"Authorization": self.pexels_key}
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            raise RuntimeError(f"No Pexels videos found for '{query}'")
        video = videos[0]
        video_files = video.get("video_files", [])
        best = sorted(
            [vf for vf in video_files if vf.get("width") and vf.get("height")],
            key=lambda x: abs(x["width"] / x["height"] - 9 / 16),
        )
        if not best:
            raise RuntimeError("No suitable video files in Pexels result")
        download_url = best[0]["link"]
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:50]
        out = tempfile.NamedTemporaryFile(suffix=".mp4", prefix=f"{safe_name}_", delete=False)
        out_path = out.name
        out.close()
        resp = httpx.get(download_url, timeout=120)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        logger.info("Downloaded fallback video to %s", out_path)
        return out_path
