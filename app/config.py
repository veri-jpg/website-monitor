"""
File ini bertugas membaca semua environment variable dari .env
dan menyediakannya sebagai satu objek `settings` yang bisa diimport
di file mana saja (models, api, scheduler, dll).

Kenapa pakai pydantic-settings bukan os.getenv() biasa?
- Otomatis validasi tipe data (misal POSTGRES_PORT harus integer, bukan string)
- Kalau ada variable wajib yang tidak diisi di .env, aplikasi akan error
  saat startup (fail fast), bukan error nyasar di tengah jalan production.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int = 5432
    database_url: str

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    # Playwright - true di production/Docker, bisa false untuk development
    # supaya browser kelihatan dan mudah didebug secara visual.
    playwright_headless: bool = True

    # Security
    encryption_key: str

    # Telegram
    telegram_bot_token: str = ""
    telegram_default_chat_id: str = ""

    # Discord
    discord_webhook_url: str = ""

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Satu instance global, diimport di seluruh aplikasi:
# from app.config import settings
settings = Settings()
