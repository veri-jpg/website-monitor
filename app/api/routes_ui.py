from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.check_result import CheckResult
from app.models.notification_rule import NotificationRule
from app.models.website import Website
from app.monitors.http_checker import check_http
from app.monitors.playwright_checker import check_playwright

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _timeago(dt) -> str:
    if not dt:
        return "Belum pernah"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = int((now - dt).total_seconds())
    if diff < 60:
        return f"{diff} detik lalu"
    if diff < 3600:
        return f"{diff // 60} menit lalu"
    if diff < 86400:
        return f"{diff // 3600} jam lalu"
    return f"{diff // 86400} hari lalu"


def _datetimefmt(dt) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%d %b %Y, %H:%M UTC")


templates.env.filters["timeago"] = _timeago
templates.env.filters["datetimefmt"] = _datetimefmt


def _rules_by_channel(rules) -> dict:
    return {r.channel: r for r in rules}


def _redirect(path: str, msg: str = "") -> RedirectResponse:
    url = f"{path}?success={quote_plus(msg)}" if msg else path
    return RedirectResponse(url, status_code=303)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    websites = db.query(Website).order_by(Website.created_at.desc()).all()

    latest_checks: dict = {}
    for w in websites:
        latest = (
            db.query(CheckResult)
            .filter(CheckResult.website_id == w.id)
            .order_by(CheckResult.checked_at.desc())
            .first()
        )
        latest_checks[w.id] = latest

    stats = {
        "total": len(websites),
        "up": sum(1 for w in websites if w.current_status == "up"),
        "down": sum(1 for w in websites if w.current_status == "down"),
        "unknown": sum(1 for w in websites if w.current_status is None),
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "websites": websites,
        "latest_checks": latest_checks,
        "stats": stats,
        "flash_success": request.query_params.get("success"),
    })


# ─── Add Website ──────────────────────────────────────────────────────────────

@router.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    return templates.TemplateResponse("website_form.html", {
        "request": request,
        "website": None,
        "rules": {},
        "error": None,
        "fd": {},
        "existing_retry_count": 3,
        "existing_retry_delay": 30,
    })


@router.post("/add")
async def create_website_ui(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    url: str = Form(...),
    check_method: str = Form("http"),
    interval_seconds: int = Form(60),
    retry_count: int = Form(3),
    retry_delay_seconds: int = Form(30),
    selector: Optional[str] = Form(None),
    username_selector: Optional[str] = Form(None),
    password_selector: Optional[str] = Form(None),
    submit_selector: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    telegram_target: Optional[str] = Form(None),
    discord_target: Optional[str] = Form(None),
    email_target: Optional[str] = Form(None),
):
    t = (telegram_target or "").strip()
    d = (discord_target or "").strip()
    e = (email_target or "").strip()

    if not any([t, d, e]):
        fd = {
            "name": name, "url": url, "check_method": check_method,
            "interval_seconds": interval_seconds, "retry_count": retry_count,
            "retry_delay_seconds": retry_delay_seconds,
            "selector": selector or "", "username_selector": username_selector or "",
            "password_selector": password_selector or "", "submit_selector": submit_selector or "",
            "username": username or "", "telegram_target": t, "discord_target": d, "email_target": e,
        }
        return templates.TemplateResponse("website_form.html", {
            "request": request,
            "website": None,
            "rules": {},
            "error": "Minimal satu channel notifikasi harus diisi (Telegram, Discord, atau Email).",
            "fd": fd,
            "existing_retry_count": retry_count,
            "existing_retry_delay": retry_delay_seconds,
        }, status_code=422)

    credentials = None
    if check_method == "playwright" and any([username_selector, password_selector]):
        credentials = {
            "username_selector": username_selector or "",
            "password_selector": password_selector or "",
            "submit_selector": submit_selector or "",
            "username": username or "",
            "password": password or "",
        }

    website = Website(
        name=name,
        url=url,
        check_method=check_method,
        interval_seconds=interval_seconds,
        selector=(selector or "").strip() or None,
        credentials=credentials,
    )
    db.add(website)
    db.flush()

    for channel, target in [("telegram", t), ("discord", d), ("email", e)]:
        if target:
            db.add(NotificationRule(
                website_id=website.id,
                channel=channel,
                target=target,
                retry_count=retry_count,
                retry_delay_seconds=retry_delay_seconds,
            ))

    db.commit()
    return _redirect("/", f"Website '{name}' berhasil ditambahkan dan mulai dimonitor!")


# ─── Website Detail ───────────────────────────────────────────────────────────

@router.get("/website/{website_id}", response_class=HTMLResponse)
def website_detail(website_id: int, request: Request, db: Session = Depends(get_db)):
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return _redirect("/")

    check_results = (
        db.query(CheckResult)
        .filter(CheckResult.website_id == website_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse("website_detail.html", {
        "request": request,
        "website": website,
        "check_results": check_results,
        "rules": _rules_by_channel(website.notification_rules),
        "flash_success": request.query_params.get("success"),
    })


# ─── Edit Website ─────────────────────────────────────────────────────────────

@router.get("/website/{website_id}/edit", response_class=HTMLResponse)
def edit_form(website_id: int, request: Request, db: Session = Depends(get_db)):
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return _redirect("/")

    rules = _rules_by_channel(website.notification_rules)
    any_rule = next(iter(rules.values()), None)

    return templates.TemplateResponse("website_form.html", {
        "request": request,
        "website": website,
        "rules": rules,
        "error": None,
        "fd": {},
        "existing_retry_count": any_rule.retry_count if any_rule else 3,
        "existing_retry_delay": any_rule.retry_delay_seconds if any_rule else 30,
    })


@router.post("/website/{website_id}/edit")
async def update_website_ui(
    website_id: int,
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    url: str = Form(...),
    check_method: str = Form("http"),
    interval_seconds: int = Form(60),
    retry_count: int = Form(3),
    retry_delay_seconds: int = Form(30),
    selector: Optional[str] = Form(None),
    username_selector: Optional[str] = Form(None),
    password_selector: Optional[str] = Form(None),
    submit_selector: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    telegram_target: Optional[str] = Form(None),
    discord_target: Optional[str] = Form(None),
    email_target: Optional[str] = Form(None),
):
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return _redirect("/")

    t = (telegram_target or "").strip()
    d = (discord_target or "").strip()
    e = (email_target or "").strip()

    if not any([t, d, e]):
        rules = _rules_by_channel(website.notification_rules)
        any_rule = next(iter(rules.values()), None)
        fd = {
            "name": name, "url": url, "check_method": check_method,
            "interval_seconds": interval_seconds, "retry_count": retry_count,
            "retry_delay_seconds": retry_delay_seconds,
            "selector": selector or "", "username_selector": username_selector or "",
            "password_selector": password_selector or "", "submit_selector": submit_selector or "",
            "username": username or "", "telegram_target": t, "discord_target": d, "email_target": e,
        }
        return templates.TemplateResponse("website_form.html", {
            "request": request,
            "website": website,
            "rules": rules,
            "error": "Minimal satu channel notifikasi harus diisi.",
            "fd": fd,
            "existing_retry_count": any_rule.retry_count if any_rule else retry_count,
            "existing_retry_delay": any_rule.retry_delay_seconds if any_rule else retry_delay_seconds,
        }, status_code=422)

    website.name = name
    website.url = url
    website.check_method = check_method
    website.interval_seconds = interval_seconds
    website.selector = (selector or "").strip() or None

    if check_method == "playwright" and any([username_selector, password_selector]):
        existing_creds = website.credentials or {}
        website.credentials = {
            "username_selector": username_selector or "",
            "password_selector": password_selector or "",
            "submit_selector": submit_selector or "",
            "username": username or existing_creds.get("username", ""),
            "password": password if password else existing_creds.get("password", ""),
        }
    elif check_method == "http":
        website.credentials = None

    existing_rules = _rules_by_channel(website.notification_rules)
    for channel, target in [("telegram", t), ("discord", d), ("email", e)]:
        if target:
            if channel in existing_rules:
                existing_rules[channel].target = target
                existing_rules[channel].retry_count = retry_count
                existing_rules[channel].retry_delay_seconds = retry_delay_seconds
            else:
                db.add(NotificationRule(
                    website_id=website_id,
                    channel=channel,
                    target=target,
                    retry_count=retry_count,
                    retry_delay_seconds=retry_delay_seconds,
                ))
        else:
            if channel in existing_rules:
                db.delete(existing_rules[channel])

    db.commit()
    return _redirect(f"/website/{website_id}", "Perubahan berhasil disimpan.")


# ─── Delete Website ───────────────────────────────────────────────────────────

@router.post("/website/{website_id}/delete")
def delete_website_ui(website_id: int, db: Session = Depends(get_db)):
    website = db.query(Website).filter(Website.id == website_id).first()
    if website:
        name = website.name
        db.delete(website)
        db.commit()
        return _redirect("/", f"Website '{name}' berhasil dihapus.")
    return _redirect("/")


# ─── Check Now (HTMX — returns updated badge HTML) ────────────────────────────

@router.post("/website/{website_id}/check", response_class=HTMLResponse)
async def check_now_htmx(website_id: int, db: Session = Depends(get_db)):
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return HTMLResponse("", status_code=404)

    if website.check_method == "playwright":
        result = await check_playwright(
            website.url, selector=website.selector, credentials=website.credentials
        )
    else:
        result = await check_http(website.url)

    cr = CheckResult(website_id=website_id, **result)
    db.add(cr)

    status = "up" if result["status"] == "success" else "down"
    website.current_status = status
    website.last_checked_at = datetime.now(timezone.utc)
    db.commit()

    if status == "up":
        return HTMLResponse(
            f'<span id="badge-{website_id}" '
            f'class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700">'
            f'<span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>UP</span>'
        )
    return HTMLResponse(
        f'<span id="badge-{website_id}" '
        f'class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700">'
        f'<span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>DOWN</span>'
    )


# ─── Check Now (detail page — runs check then redirects back) ─────────────────

@router.post("/website/{website_id}/check-redirect")
async def check_now_redirect(website_id: int, db: Session = Depends(get_db)):
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        return _redirect("/")

    if website.check_method == "playwright":
        result = await check_playwright(
            website.url, selector=website.selector, credentials=website.credentials
        )
    else:
        result = await check_http(website.url)

    cr = CheckResult(website_id=website_id, **result)
    db.add(cr)

    status = "up" if result["status"] == "success" else "down"
    website.current_status = status
    website.last_checked_at = datetime.now(timezone.utc)
    db.commit()

    msg = f"Pengecekan selesai: {status.upper()}"
    if result.get("response_time_ms"):
        msg += f" ({result['response_time_ms']} ms)"
    return _redirect(f"/website/{website_id}", msg)
