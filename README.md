# 🔍 Universal Website Monitoring Platform

Platform monitoring website production-grade yang mendukung dua strategi pengecekan: **HTTP/API check** (ringan, untuk endpoint publik) dan **Browser Automation** (via Playwright, untuk website yang butuh login dan interaksi elemen). Dibangun modular sehingga bisa berkembang dari memonitor 1 hingga ratusan website tanpa mengubah arsitektur utama.

> **Catatan**: Project ini dibangun sebagai portofolio sekaligus sistem yang benar-benar bisa dipakai — bukan sekedar tutorial CRUD biasa.

---

## ✨ Fitur Utama

- **Dual monitoring engine** — HTTPX untuk HTTP/API check, Playwright untuk browser automation (login, selector checking)
- **Scheduler otomatis** — APScheduler polling tiap 10 detik, menjalankan pengecekan sesuai interval per-website
- **Concurrent execution** — banyak website dicek bersamaan via `asyncio.gather`, bukan satu-satu berurutan
- **Retry mechanism** — kegagalan sementara tidak langsung dianggap down, retry beberapa kali dulu sebelum kirim notifikasi
- **Edge-triggered notification** — notifikasi hanya terkirim saat **status berubah** (up→down atau down→up), bukan setiap kali polling menemukan website masih down (anti-spam)
- **Multi-channel notification** — Telegram Bot API dan Email (SMTP), mudah ditambah channel baru
- **Background task isolation** — proses retry per-website berjalan independen, tidak memblokir pengecekan website lain
- **Flag locking** (`is_checking`) — mencegah satu website diproses dua kali bersamaan walau scheduler sudah polling lagi
- **Deployment siap pakai** — Docker Compose dengan entrypoint yang otomatis menjalankan database migration sebelum aplikasi start

---

## 🛠️ Tech Stack

| Kategori | Teknologi | Kegunaan |
|---|---|---|
| **Web Framework** | FastAPI | REST API dengan auto-generated Swagger docs |
| **Database** | PostgreSQL | Penyimpanan konfigurasi dan histori pengecekan |
| **ORM** | SQLAlchemy | Model database dan query builder |
| **Migrations** | Alembic | Versioning skema database |
| **Validation** | Pydantic | Validasi request/response + type safety |
| **Scheduler** | APScheduler | Job scheduling dengan trigger interval |
| **HTTP Client** | HTTPX | Async HTTP request untuk pengecekan API/website |
| **Browser Automation** | Playwright | Chromium headless untuk login flow dan selector check |
| **Notifications** | python-telegram-bot | Pengiriman notifikasi via Telegram Bot API |
| **Notifications** | smtplib (stdlib) | Pengiriman email via SMTP (Gmail App Password) |
| **Containerization** | Docker + Docker Compose | Isolated deployment, portabel ke VPS mana pun |
| **Security** | cryptography (Fernet) | Enkripsi kredensial login yang tersimpan di database |
| **Config** | pydantic-settings | Manajemen environment variables dengan type validation |

---

## 🏗️ Arsitektur

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │
│  │  /websites│  │/check-   │  │  /notification-rules     │  │
│  │  CRUD    │  │results   │  │  CRUD                    │  │
│  └────┬─────┘  └──────────┘  └──────────────────────────┘  │
│       │                                                     │
│  ┌────▼──────────────────────────────────────────────────┐  │
│  │              APScheduler (polling tiap 10s)           │  │
│  │                                                       │  │
│  │  run_due_checks() → asyncio.gather([                  │  │
│  │    _process_website(A),  ← background task           │  │
│  │    _process_website(B),  ← background task           │  │
│  │    _process_website(C),  ← background task           │  │
│  │  ])                                                   │  │
│  └────┬──────────────────────────────────────────────────┘  │
│       │                                                     │
│  ┌────▼──────────────────┐  ┌────────────────────────────┐  │
│  │   Monitoring Engine   │  │   Notification Engine      │  │
│  │                       │  │                            │  │
│  │  check_method=http    │  │  Edge-triggered:           │  │
│  │  → HTTPX async        │  │  previous ≠ current →      │  │
│  │                       │  │  → Telegram Bot API        │  │
│  │  check_method=        │  │  → SMTP Email              │  │
│  │    playwright         │  │                            │  │
│  │  → Chromium headless  │  │                            │  │
│  └───────────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │     PostgreSQL      │
              │                     │
              │  websites           │
              │  check_results      │
              │  notification_rules │
              └─────────────────────┘
```

---

## 📁 Struktur Project

```
website-monitor/
├── app/
│   ├── main.py                  # Entry point FastAPI
│   ├── config.py                # Settings dari .env (pydantic-settings)
│   ├── database.py              # Koneksi SQLAlchemy + session
│   ├── api/
│   │   ├── routes_website.py        # CRUD website + manual check-now
│   │   ├── routes_check_result.py   # Read-only histori pengecekan
│   │   └── routes_notification_rule.py  # CRUD notification rules
│   ├── models/
│   │   ├── website.py           # Tabel websites
│   │   ├── check_result.py      # Tabel check_results
│   │   └── notification_rule.py # Tabel notification_rules
│   ├── schemas/
│   │   ├── website.py           # Pydantic: Create/Update/Response
│   │   └── check_result.py      # Pydantic: Response only (read-only)
│   ├── monitors/
│   │   ├── http_checker.py      # HTTPX async checker
│   │   └── playwright_checker.py # Playwright browser checker
│   ├── notifiers/
│   │   ├── telegram.py          # Telegram Bot API
│   │   ├── email.py             # SMTP Email
│   │   └── placeholder.py       # Fallback untuk channel belum diimplementasi
│   └── scheduler/
│       ├── scheduler.py         # APScheduler setup + lifecycle hooks
│       └── jobs.py              # Polling logic, retry, edge-triggered notif
├── alembic/                     # Database migration history
├── entrypoint.sh                # Docker entrypoint (migration → uvicorn)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Cara Menjalankan

### Prerequisites
- Docker & Docker Compose
- (Opsional, untuk development lokal) Python 3.12+

### 1. Clone repository
```bash
git clone https://github.com/username/website-monitor.git
cd website-monitor
```

### 2. Setup konfigurasi
```bash
cp .env.example .env.docker
```

Edit `.env.docker` dan isi nilai-nilainya:

```env
# Database
POSTGRES_USER=monitor_user
POSTGRES_PASSWORD=password_kuat_kamu
POSTGRES_DB=website_monitor
POSTGRES_HOST=db
DATABASE_URL=postgresql://monitor_user:password_kuat_kamu@db:5432/website_monitor

# Security - generate dengan command di bawah
ENCRYPTION_KEY=

# Telegram (opsional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_DEFAULT_CHAT_ID=

# Email SMTP (opsional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
```

Generate `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Jalankan
```bash
docker compose up --build
```

Aplikasi otomatis:
- Menjalankan database migration (`alembic upgrade head`)
- Menyalakan FastAPI server di port 8000
- Menyalakan scheduler monitoring

### 4. Akses
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/`

---

## 📖 Cara Penggunaan

### Tambah website untuk dimonitor

**HTTP check** (cek status code dan response time):
```bash
POST /websites/
{
  "name": "My API",
  "url": "https://api.example.com/health",
  "check_method": "http",
  "interval_seconds": 60
}
```

**Playwright check** (login + cek elemen):
```bash
POST /websites/
{
  "name": "Admin Dashboard",
  "url": "https://admin.example.com/login",
  "check_method": "playwright",
  "interval_seconds": 300,
  "selector": "text=Welcome back",
  "credentials": {
    "username": "admin",
    "password": "secret",
    "username_selector": "#username",
    "password_selector": "#password",
    "submit_selector": "button[type='submit']"
  }
}
```

### Setup notifikasi
```bash
POST /notification-rules/
{
  "website_id": 1,
  "channel": "telegram",
  "target": "YOUR_CHAT_ID",
  "retry_count": 3,
  "retry_delay_seconds": 30
}
```

### Trigger pengecekan manual
```bash
POST /websites/{id}/check-now
```

### Lihat histori pengecekan
```bash
GET /check-results/?website_id=1&limit=50
```

---

## 🔄 Alur Monitoring

```
Scheduler polling (tiap 10 detik)
  └─> Cek website mana yang sudah due
       └─> Lepas ke background task (asyncio.create_task)
            └─> Jalankan check (HTTP atau Playwright)
                 ├─> Sukses → simpan ke check_results
                 └─> Gagal → retry sesuai konfigurasi
                              ├─> Retry berhasil → simpan, status = "up"
                              └─> Semua retry gagal → simpan, status = "down"
                                   └─> Edge-triggered check:
                                        ├─> Status berubah? → KIRIM NOTIFIKASI
                                        └─> Status sama? → tidak kirim (anti-spam)
```

---

## 🗄️ Database Schema

```
websites
├── id, name, url
├── check_method (http | playwright)
├── interval_seconds
├── selector (untuk Playwright)
├── credentials (JSON, encrypted)
├── is_active, is_checking
├── current_status (up | down | NULL)
└── last_checked_at, created_at

check_results
├── id, website_id (FK)
├── status (success | failed)
├── status_code, response_time_ms
├── error_message, screenshot_path
└── checked_at

notification_rules
├── id, website_id (FK)
├── channel (telegram | email | discord)
├── target (chat_id | email address | webhook url)
└── retry_count, retry_delay_seconds
```

---

## ⚙️ Environment Variables

| Variable | Wajib | Deskripsi |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `ENCRYPTION_KEY` | ✅ | Fernet key untuk enkripsi credentials |
| `PLAYWRIGHT_HEADLESS` | ✅ | `true` untuk production, `false` untuk development |
| `TELEGRAM_BOT_TOKEN` | opsional | Token dari @BotFather |
| `TELEGRAM_DEFAULT_CHAT_ID` | opsional | Chat ID tujuan notifikasi |
| `SMTP_HOST` | opsional | SMTP server (contoh: smtp.gmail.com) |
| `SMTP_PORT` | opsional | SMTP port (587 untuk TLS) |
| `SMTP_USERNAME` | opsional | Email pengirim |
| `SMTP_PASSWORD` | opsional | App Password (bukan password biasa) |

---

## 🧠 Keputusan Desain yang Dipertimbangkan

**Polling vs per-website job scheduler** — dipilih polling karena lebih scalable: jumlah job di scheduler tetap 1 apa pun jumlah website, beda dengan per-website job yang makin berat seiring website bertambah.

**`asyncio.create_task` vs `asyncio.gather`** — dipilih `create_task` supaya satu website yang retry lama tidak memblokir putaran polling berikutnya.

**Edge-triggered notification** — notifikasi hanya saat ada transisi status (bukan setiap gagal) untuk mencegah alert fatigue pada klien.

**`is_checking` flag** — locking sederhana untuk mencegah satu website diproses dua kali bersamaan, menghindari duplikasi `check_results`.

**Interface seragam antar engine** — `check_http` dan `check_playwright` mengembalikan struktur dictionary yang identik, sehingga scheduler tidak perlu tahu perbedaan keduanya.

---

## 📝 License

MIT