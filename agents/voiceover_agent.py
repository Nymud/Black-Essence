import asyncio
import logging
import tempfile
import edge_tts
import httpx

from utils.config import Config
from utils.fallbacks import FallbackChain

logger = logging.getLogger(__name__)


class VoiceoverAgent:
    def __init__(self):
        self.edge_tts_voice = Config.EDGE_TTS_VOICE
        self.elevenlabs_key = Config.ELEVENLABS_API_KEY
        self.elevenlabs_voice = Config.ELEVENLABS_VOICE_ID

    def _edge_tts_sync(self, text: str) -> str:
        return asyncio.run(self._edge_tts_async(text))

    async def _edge_tts_async(self, text: str) -> str:
        out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        out_path = out.name
        out.close()
        tts = edge_tts.Communicate(text=text, voice=self.edge_tts_voice)
        await tts.save(out_path)
        logger.info("edge-tts saved audio to %s", out_path)
        return out_path

    def _elevenlabs_tts(self, text: str) -> str:
        if not self.elevenlabs_key:
            raise RuntimeError("ElevenLabs API key not configured")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key,
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
        }

        resp = httpx.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()

        out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        out_path = out.name
        out.close()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        logger.info("ElevenLabs saved audio to %s", out_path)
        return out_path

    def generate_voiceover(self, script: str) -> str:
        chain = FallbackChain("VoiceoverAgent")
        chain.add_handler(self._edge_tts_sync, "edge-tts")
        chain.add_handler(self._elevenlabs_tts, "ElevenLabs")
        return chain.execute(script)
