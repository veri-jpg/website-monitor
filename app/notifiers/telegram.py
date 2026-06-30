"""
Notifier untuk mengirim notifikasi lewat Telegram Bot API.
"""

import logging

from telegram import Bot
from telegram.error import TelegramError

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_notification(target: str, message: str) -> bool:
    """
    Mengirim pesan ke Telegram.

    `target` adalah chat_id tujuan (bisa beda dengan TELEGRAM_DEFAULT_CHAT_ID
    kalau notification_rule menentukan chat_id lain secara spesifik).

    Mengembalikan True kalau berhasil terkirim, False kalau gagal -
    SENGAJA tidak melempar exception, supaya kegagalan kirim notifikasi
    tidak ikut menggagalkan proses pengecekan website itu sendiri.
    """
    bot_token = settings.telegram_bot_token

    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN belum diisi di .env - notifikasi Telegram dilewati.")
        return False

    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=target, text=message)
        logger.info(f"Notifikasi Telegram terkirim ke chat_id={target}")
        return True

    except TelegramError as e:
        logger.error(f"Gagal mengirim notifikasi Telegram ke chat_id={target}: {e}")
        return False

    except Exception as e:
        logger.error(f"Error tak terduga saat mengirim notifikasi Telegram: {e}")
        return False