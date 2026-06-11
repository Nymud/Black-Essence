import os
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
        self.youtube_creds = self._load_youtube_creds()

    def _load_youtube_creds(self):
        raw = Config.YOUTUBE_TOKEN
        if not raw:
            return None
        if raw.startswith("pickle://"):
            import pickle, json
            path = raw[len("pickle://"):]
            if os.path.exists(path):
                with open(path, "rb") as f:
                    token = pickle.load(f)
                cs_path = os.path.join(os.path.dirname(path), "client_secret.json")
                client_cfg = {"client_id": "", "client_secret": ""}
                if os.path.exists(cs_path):
                    with open(cs_path) as f:
                        client_cfg = json.load(f).get("installed", client_cfg)
                from google.oauth2.credentials import Credentials
                return Credentials(
                    token=token.get("access_token") or token.get("token", ""),
                    refresh_token=token.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_cfg["client_id"],
                    client_secret=client_cfg["client_secret"],
                    scopes=["https://www.googleapis.com/auth/youtube.upload"],
                )
        return None

    def publish_youtube_shorts(self, video_path: str, title: str, description: str, thumbnail_path: str = None) -> str:
        try:
            return self._youtube_upload(video_path, title, description, thumbnail_path)
        except Exception as e:
            logger.error("YouTube publishing failed: %s", e)
            return None

    def _youtube_upload(self, video_path: str, title: str, description: str, thumbnail_path: str = None) -> str:
        if not self.youtube_creds:
            logger.warning("YouTube OAuth token not configured, skipping upload")
            return None
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube = build("youtube", "v3", credentials=self.youtube_creds)
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

    def _refresh_instagram_token(self):
        if not Config.INSTAGRAM_APP_SECRET:
            return self.instagram_token
        try:
            r = httpx.get("https://graph.instagram.com/refresh_access_token", params={
                "grant_type": "ig_refresh_token",
                "access_token": self.instagram_token,
            })
            if r.ok:
                data = r.json()
                self.instagram_token = data["access_token"]
                logger.info("Instagram token refreshed")
        except Exception as e:
            logger.warning("Failed to refresh Instagram token: %s", e)
        return self.instagram_token

    def _instagram_upload(self, video_path: str, caption: str) -> str:
        self._refresh_instagram_token()
        logger.warning("Instagram Reels publishing requires Meta App Review for 'instagram_business_content_publish' permission. Skipping upload.")
        return None

    def publish_all(self, video_path: str, vertical_path: str, title: str, description: str, thumbnail_path: str = None) -> PublishingResult:
        result = PublishingResult()

        result.youtube_url = self.publish_youtube_shorts(video_path, title, description, thumbnail_path)

        result.tiktok_url = self.publish_tiktok(vertical_path, description)

        result.instagram_url = self.publish_instagram_reel(vertical_path, description)

        return result
