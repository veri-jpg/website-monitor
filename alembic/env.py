"""
File ini dijalankan otomatis oleh Alembic setiap kali kamu menjalankan
command `alembic revision --autogenerate` atau `alembic upgrade head`.

Tugasnya:
1. Mengambil DATABASE_URL dari .env (lewat app.config.settings)
2. Mengimpor semua model supaya Alembic tahu struktur tabel yang seharusnya ada
3. Membandingkan struktur model Python vs struktur database saat ini
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.config import settings
from app.database import Base

# Import semua model di sini supaya Alembic bisa "melihat" mereka.
# Kalau ada model baru nanti, wajib ditambahkan importnya di sini juga.
from app.models.website import Website
from app.models.check_result import CheckResult
from app.models.notification_rule import NotificationRule

config = context.config

# Ambil URL database dari .env, bukan dari alembic.ini
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata inilah yang dibandingkan Alembic terhadap database asli
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()