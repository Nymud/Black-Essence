import logging
import os
import tempfile
import httpx

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class BrollAgent:
    def __init__(self):
        self.pexels_key = Config.PEXELS_API_KEY
        self.giphy_key = Config.GIPHY_API_KEY
        self.pixabay_key = Config.PIXABAY_API_KEY

    def _search_pexels(self, query: str) -> str:
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
        return self._download_clip(download_url, query)

    def _search_pixabay(self, query: str) -> str:
        if not self.pixabay_key:
            raise RuntimeError("Pixabay API key not configured")

        url = "https://pixabay.com/api/videos/"
        params = {"key": self.pixabay_key, "q": query, "per_page": 3, "orientation": "vertical"}
        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        hits = data.get("hits", [])
        if not hits:
            raise RuntimeError(f"No Pixabay videos found for '{query}'")

        video = hits[0]
        videos_field = video.get("videos", {})
        small = videos_field.get("small", {}) or videos_field.get("medium", {}) or videos_field.get("large", {})
        download_url = small.get("url")
        if not download_url:
            raise RuntimeError("No usable video URL from Pixabay")

        return self._download_clip(download_url, query)

    def _search_giphy(self, query: str) -> str:
        if not self.giphy_key:
            raise RuntimeError("GIPHY API key not configured")

        url = "https://api.giphy.com/v1/gifs/search"
        params = {"api_key": self.giphy_key, "q": query, "limit": 1, "rating": "g"}
        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        gifs = data.get("data", [])
        if not gifs:
            raise RuntimeError(f"No GIPHY results for '{query}'")

        download_url = gifs[0]["images"]["original"]["mp4"]
        return self._download_clip(download_url, query)

    def _download_clip(self, url: str, query: str) -> str:
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:50]
        out = tempfile.NamedTemporaryFile(suffix=".mp4", prefix=f"{safe_name}_", delete=False)
        out_path = out.name
        out.close()

        resp = httpx.get(url, timeout=120)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        logger.info("Downloaded clip to %s", out_path)
        return out_path

    def get_clip(self, query: str) -> str:
        chain = FallbackChain("BrollAgent")
        chain.add_handler(self._search_pexels, "Pexels")
        chain.add_handler(self._search_pixabay, "Pixabay")
        chain.add_handler(self._search_giphy, "GIPHY")
        return chain.execute(query)
