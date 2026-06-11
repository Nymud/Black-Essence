import asyncio, sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from telegram import Bot
from utils.config import Config

async def main():
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    updates = await bot.get_updates()
    print(f"Found {len(updates)} pending update(s):")
    for u in updates[-5:]:
        if u.message and u.message.text:
            print(f"  From {u.message.from_user.username or '??'}: {u.message.text}")
        elif u.message:
            print(f"  From {u.message.from_user.username or '??'}: [non-text message]")

if __name__ == "__main__":
    asyncio.run(main())
