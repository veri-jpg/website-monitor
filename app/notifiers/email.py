"""
Notifier untuk mengirim notifikasi lewat Email via SMTP.
Menggunakan smtplib bawaan Python - tidak butuh library tambahan.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email_notification(target: str, message: str) -> bool:
    """
    Mengirim email notifikasi ke alamat email tujuan.

    `target` adalah alamat email tujuan.

    Mengembalikan True kalau berhasil, False kalau gagal -
    SENGAJA tidak melempar exception, konsisten dengan prinsip
    fault isolation yang sama seperti notifier Telegram.
    """
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("SMTP credentials belum diisi di .env - notifikasi Email dilewati.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from_email
        msg["To"] = target
        msg["Subject"] = "🚨 Website Monitor Alert"
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)

        logger.info(f"Notifikasi Email terkirim ke {target}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Gagal autentikasi SMTP - periksa SMTP_USERNAME dan SMTP_PASSWORD di .env")
        return False

    except smtplib.SMTPException as e:
        logger.error(f"Gagal mengirim Email ke {target}: {e}")
        return False

    except Exception as e:
        logger.error(f"Error tak terduga saat mengirim Email: {e}")
        return False