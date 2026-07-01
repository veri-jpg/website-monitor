"""
Notifier untuk mengirim notifikasi lewat Discord Webhook.

`target` adalah webhook URL Discord (bisa berbeda per notification_rule,
sehingga bisa diarahkan ke channel berbeda untuk website berbeda).
Kalau target kosong, fallback ke DISCORD_WEBHOOK_URL dari .env.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_discord_notification(target: str, message: str) -> bool:
    """
    Mengirim embed ke Discord via webhook URL.

    Mengembalikan True kalau berhasil, False kalau gagal -
    konsisten dengan prinsip fault isolation notifier lainnya.
    """
    webhook_url = target or settings.discord_webhook_url

    if not webhook_url:
        logger.warning("Discord webhook URL belum diisi - notifikasi Discord dilewati.")
        return False

    payload = {"embeds": [{"description": message, "color": 0xFF0000 if "DOWN" in message else 0x00FF00}]}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        logger.info(f"Notifikasi Discord terkirim ke webhook.")
        return True

    except httpx.HTTPStatusError as e:
        logger.error(f"Gagal kirim notifikasi Discord (HTTP {e.response.status_code}): {e}")
        return False

    except httpx.RequestError as e:
        logger.error(f"Gagal kirim notifikasi Discord (koneksi): {e}")
        return False

    except Exception as e:
        logger.error(f"Error tak terduga saat mengirim notifikasi Discord: {e}")
        return False
