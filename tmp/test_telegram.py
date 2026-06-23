import httpx
from utils.config import Config

token = Config.TELEGRAM_BOT_TOKEN
chat_id = Config.TELEGRAM_ADMIN_CHAT_ID
r = httpx.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": "🔔 Black Essence is now running on Heroku! You will receive notifications here when videos are ready."},
    timeout=10,
)
print(r.status_code, r.text[:200])
