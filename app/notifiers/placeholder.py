"""
Placeholder notifier - SEMENTARA hanya logging, belum benar-benar
mengirim apa pun ke Telegram/Discord/Email.

Akan diganti dengan implementasi asli setelah logic edge-triggered
notification ini terverifikasi bekerja dengan benar.
"""

import logging

logger = logging.getLogger(__name__)


async def send_notification(website_name: str, channel: str, target: str, message: str) -> None:
    """
    Placeholder pengiriman notifikasi.
    Untuk sekarang cuma mencatat ke log, supaya logic KAPAN notifikasi
    harus dikirim bisa diverifikasi dulu sebelum membangun pengiriman aslinya.
    """
    logger.info(
        f"[NOTIFIKASI-SIMULASI] -> channel={channel}, target={target} | "
        f"{website_name}: {message}"
    )