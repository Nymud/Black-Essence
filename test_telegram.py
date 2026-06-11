import asyncio, sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from bot.telegram_bot import TelegramApprovalBot

async def main():
    bot = TelegramApprovalBot()
    await bot.start()
    await bot.send_alert("Test message from Black Essence - bot is working!")
    print("Sent test alert - check Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
