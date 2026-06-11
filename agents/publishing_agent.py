import logging
import httpx

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class PublishingResult:
    def __init__(self):
        self.youtube_url = None
        self.tiktok_url = None
        self.instagram_url = None
        self.errors = []


class PublishingAgent:
    def __init__(self):
        self.tiktok_token = Config.TIKTOK_ACCESS_TOKEN
        self.instagram_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.youtube_key = Config.YOUTUBE_API_KEY

    def publish_youtube_shorts(self, video_path: str, title: str, description: str, thumbnail_path: str = None) -> str:
        try:
            return self._youtube_upload(video_path, title, description, thumbnail_path)
        except Exception as e:
            logger.error("YouTube publishing failed: %s", e)
            return None

    def _youtube_upload(self, video_path: str, title: str, description: str, thumbnail_path: str = None) -> str:
        if not self.youtube_key:
            logger.warning("YouTube API key not configured, skipping upload")
            return None
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube = build("youtube", "v3", developerKey=self.youtube_key)
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": ["blackhistory", "education", "shorts"],
                "categoryId": "27",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )
        response = request.execute()
        video_id = response.get("id")
        youtube_url = f"https://youtube.com/watch?v={video_id}"
        logger.info("Uploaded to YouTube: %s", youtube_url)

        if thumbnail_path and video_id:
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path),
                ).execute()
                logger.info("Thumbnail set for YouTube video %s", video_id)
            except Exception as e:
                logger.warning("Failed to set thumbnail: %s", e)

        return youtube_url

    def publish_tiktok(self, video_path: str, description: str) -> str:
        if not self.tiktok_token:
            logger.warning("TikTok token not configured, skipping")
            return None
        try:
            return self._tiktok_upload(video_path, description)
        except Exception as e:
            logger.error("TikTok publishing failed: %s", e)
            return None

    def _tiktok_upload(self, video_path: str, description: str) -> str:
        url = "https://open-api.tiktok.com/share/video/upload/"
        headers = {"access-token": self.tiktok_token}
        with open(video_path, "rb") as f:
            files = {"video": f}
            data = {"description": description[:150]}
            resp = httpx.post(url, headers=headers, files=files, data=data, timeout=300)
        resp.raise_for_status()
        result = resp.json()
        share_url = result.get("data", {}).get("share_url", "")
        logger.info("Uploaded to TikTok: %s", share_url)
        return share_url

    def publish_instagram_reel(self, video_path: str, caption: str) -> str:
        if not self.instagram_token:
            logger.warning("Instagram token not configured, skipping")
            return None
        try:
            return self._instagram_upload(video_path, caption)
        except Exception as e:
            logger.error("Instagram publishing failed: %s", e)
            return None

    def _instagram_upload(self, video_path: str, caption: str) -> str:
        graph_url = f"https://graph.instagram.com/v12.0/me/media"
        with open(video_path, "rb") as f:
            files = {"video": f}
            data = {
                "caption": caption[:2200],
                "access_token": self.instagram_token,
                "media_type": "REELS",
            }
            resp = httpx.post(graph_url, data=data, files=files, timeout=300)
        resp.raise_for_status()
        media_id = resp.json().get("id")
        publish_url = f"https://graph.instagram.com/v12.0/me/media_publish"
        pub_resp = httpx.post(publish_url, data={
            "creation_id": media_id,
            "access_token": self.instagram_token,
        }, timeout=60)
        pub_resp.raise_for_status()
        ig_url = f"https://instagram.com/p/{media_id}"
        logger.info("Uploaded to Instagram: %s", ig_url)
        return ig_url

    def publish_all(self, video_path: str, vertical_path: str, title: str, description: str, thumbnail_path: str = None) -> PublishingResult:
        result = PublishingResult()

        result.youtube_url = self.publish_youtube_shorts(video_path, title, description, thumbnail_path)

        result.tiktok_url = self.publish_tiktok(vertical_path, description)

        result.instagram_url = self.publish_instagram_reel(vertical_path, description)

        return result
