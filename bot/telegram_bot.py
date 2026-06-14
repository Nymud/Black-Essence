import asyncio
import logging
import threading
from datetime import datetime

from telegram import Bot, InputMediaVideo, InputMediaPhoto
from telegram.error import TelegramError

from utils.config import Config

logger = logging.getLogger(__name__)


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequest:
    def __init__(self, video_path: str, thumbnail_path: str, topic: str):
        self.video_path = video_path
        self.thumbnail_path = thumbnail_path
        self.topic = topic
        self.status = ApprovalStatus.PENDING
        self.feedback = ""
        self.timestamp = datetime.now()


class TelegramApprovalBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.admin_chat_id = Config.TELEGRAM_ADMIN_CHAT_ID
        self.bot = None
        self._pending_approvals = {}
        self._approval_event = threading.Event()

    async def start(self):
        if not self.token:
            logger.warning("Telegram bot token not configured, bot disabled")
            return
        self.bot = Bot(token=self.token)
        logger.info("Telegram bot initialized")

    def _ensure_bot(self):
        if not self.bot and self.token:
            self.bot = Bot(token=self.token)
        return self.bot is not None

    async def send_alert(self, message: str):
        if not self._ensure_bot():
            logger.error("Cannot send alert: bot not initialized")
            return
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=f"{message}",
                parse_mode="HTML",
            )
            logger.info("Alert sent to admin")
        except TelegramError as e:
            logger.error("Failed to send alert: %s", e)

    async def request_approval(self, video_path: str, thumbnail_path: str, topic: str, timeout: int = 86400) -> ApprovalRequest:
        if not self._ensure_bot():
            logger.warning("Bot not configured, auto-approving")
            req = ApprovalRequest(video_path, thumbnail_path, topic)
            req.status = ApprovalStatus.APPROVED
            return req

        req = ApprovalRequest(video_path, thumbnail_path, topic)
        req_id = str(id(req))
        self._pending_approvals[req_id] = req
        self._approval_event.clear()

        try:
            with open(video_path, "rb") as vf, open(thumbnail_path, "rb") as tf:
                await self.bot.send_media_group(
                    chat_id=self.admin_chat_id,
                    media=[
                        InputMediaVideo(vf, caption=f"Preview: {topic}"),
                        InputMediaPhoto(tf, caption="Thumbnail"),
                    ],
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=120,
                )

            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=(
                    f"<b>Approval Required</b>\n"
                    f"Topic: {topic}\n"
                    f"Reply with:\n"
                    f"<code>/approve {req_id}</code> - to approve and publish\n"
                    f"<code>/reject {req_id} reason</code> - to reject\n"
                    f"<code>/feedback {req_id} your notes</code> - to give feedback"
                ),
                parse_mode="HTML",
            )
            logger.info("Approval request sent for: %s", topic)
        except TelegramError as e:
            logger.error("Failed to send approval request: %s", e)
            req.status = ApprovalStatus.APPROVED
            return req

        self._approval_event.wait(timeout=timeout)  # 24h default in production

        return req

    async def handle_callback(self, update):
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        chat_id = update.message.chat_id

        if str(chat_id) != self.admin_chat_id:
            await self.bot.send_message(chat_id=chat_id, text="Unauthorized")
            return

        if text.startswith("/approve"):
            parts = text.split(maxsplit=1)
            req_id = parts[1] if len(parts) > 1 else ""
            req = self._pending_approvals.get(req_id)
            if req:
                req.status = ApprovalStatus.APPROVED
                self._approval_event.set()
                await self.bot.send_message(chat_id=chat_id, text=f"Approved: {req.topic}")
            else:
                await self.bot.send_message(chat_id=chat_id, text="Invalid request ID")

        elif text.startswith("/reject"):
            parts = text.split(maxsplit=2)
            req_id = parts[1] if len(parts) > 1 else ""
            reason = parts[2] if len(parts) > 2 else "No reason given"
            req = self._pending_approvals.get(req_id)
            if req:
                req.status = ApprovalStatus.REJECTED
                req.feedback = reason
                self._approval_event.set()
                await self.bot.send_message(chat_id=chat_id, text=f"Rejected: {req.topic}\nReason: {reason}")
            else:
                await self.bot.send_message(chat_id=chat_id, text="Invalid request ID")

        elif text.startswith("/feedback"):
            parts = text.split(maxsplit=2)
            req_id = parts[1] if len(parts) > 1 else ""
            feedback = parts[2] if len(parts) > 2 else ""
            req = self._pending_approvals.get(req_id)
            if req:
                req.feedback = feedback
                await self.bot.send_message(chat_id=chat_id, text=f"Feedback recorded for {req.topic}")

    def run_polling(self):
        if not self._ensure_bot():
            return
        from telegram.ext import Application, MessageHandler, filters

        app = Application.builder().token(self.token).build()

        async def handle(update, context):
            await self.handle_callback(update)

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
        app.add_handler(MessageHandler(filters.COMMAND, handle))

        logger.info("Telegram bot polling started")
        app.run_polling(stop_signals=[])
