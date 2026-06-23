import httpx, json, os, sys

token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")

print(f"Token: {token[:20]}..." if token else "NO TOKEN")
print(f"Chat ID: {chat_id}" if chat_id else "NO CHAT ID")

if token and chat_id:
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": int(chat_id), "text": "🔔 Black Essence test message from Heroku!"},
        timeout=15,
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:300]}")
else:
    print("Missing token or chat_id!")
