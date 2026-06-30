"""
Monitoring engine untuk pengecekan berbasis browser (Playwright).
Dipakai untuk website yang membutuhkan interaksi - login, lalu mengecek
apakah elemen tertentu (selector) ada/tidak ada di halaman.

Struktur hasil yang dikembalikan SENGAJA dibuat identik dengan check_http,
supaya scheduler (jobs.py) bisa memanggil fungsi ini secara seragam tanpa
perlu tahu detail bedanya HTTP check vs browser check.
"""

import time
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.config import settings


async def check_playwright(
    url: str,
    selector: Optional[str] = None,
    credentials: Optional[dict] = None,
    timeout_seconds: int = 15,
) -> dict:
    """
    Melakukan satu kali pengecekan berbasis browser terhadap sebuah URL.

    - Kalau `credentials` diisi (berisi username_selector, password_selector,
      submit_selector, username, password), Playwright akan login dulu.
    - Kalau `selector` diisi, Playwright akan mengecek apakah elemen itu
      muncul di halaman setelah (opsional) proses login.

    Mengembalikan dictionary dengan struktur SAMA seperti check_http:
        {
            "status": "success" atau "failed",
            "status_code": None (tidak relevan untuk browser check),
            "response_time_ms": int,
            "error_message": str atau None,
        }
    """
    start_time = time.monotonic()

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=settings.playwright_headless)
            page = await browser.new_page()

            try:
                await page.goto(url, timeout=timeout_seconds * 1000)

                if credentials:
                    await page.fill(credentials["username_selector"], credentials["username"])
                    await page.fill(credentials["password_selector"], credentials["password"])
                    await page.click(credentials["submit_selector"])
                    await page.wait_for_load_state("networkidle", timeout=timeout_seconds * 1000)

                if selector:
                    await page.wait_for_selector(selector, timeout=timeout_seconds * 1000)

                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return {
                    "status": "success",
                    "status_code": None,
                    "response_time_ms": elapsed_ms,
                    "error_message": None,
                }

            finally:
                await browser.close()

    except PlaywrightTimeoutError:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "status": "failed",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Timeout - elemen atau halaman tidak merespons dalam {timeout_seconds} detik",
        }

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "status": "failed",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Error tak terduga: {str(e)}",
        }