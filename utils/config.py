import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")

    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
    HF_STABLE_DIFFUSION_MODEL = os.getenv("HF_STABLE_DIFFUSION_MODEL", "runwayml/stable-diffusion-v1-5")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")

    ANALYTIX_CLIENT_ID = os.getenv("ANALYTIX_CLIENT_ID", "")
    ANALYTIX_CLIENT_SECRET = os.getenv("ANALYTIX_CLIENT_SECRET", "")

    TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    SCHEDULE_CSV = os.getenv("SCHEDULE_CSV", "schedule.csv")
    OPTIMIZATION_RULES_PATH = os.getenv("OPTIMIZATION_RULES_PATH", "optimization_rules.json")

    EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
