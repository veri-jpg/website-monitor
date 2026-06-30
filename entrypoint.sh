#!/bin/sh
set -e

echo "Menjalankan database migration..."
alembic upgrade head

echo "Migration selesai. Menjalankan aplikasi..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000