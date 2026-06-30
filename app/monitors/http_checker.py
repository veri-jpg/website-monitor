"""
Monitoring engine untuk pengecekan HTTP/API sederhana, menggunakan HTTPX.
Dipakai untuk website yang tidak butuh interaksi browser (cukup cek status code,
response time, dan opsional isi response).

Versi async - supaya scheduler bisa mengecek banyak website secara
bersamaan (concurrent), bukan satu-satu secara berurutan.
"""

import time

import httpx


async def check_http(url: str, timeout_seconds: int = 10) -> dict:
    """
    Melakukan satu kali pengecekan HTTP terhadap sebuah URL secara async.

    Mengembalikan dictionary dengan struktur yang nantinya langsung
    cocok untuk disimpan sebagai satu baris CheckResult:
        {
            "status": "success" atau "failed",
            "status_code": int atau None,
            "response_time_ms": int atau None,
            "error_message": str atau None,
        }

    Fungsi ini SENGAJA tidak pernah melempar exception ke pemanggilnya -
    semua kemungkinan error ditangkap di sini, supaya satu website yang
    error tidak menghentikan proses pengecekan website lain.
    """
    start_time = time.monotonic()

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=timeout_seconds)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        is_success = 200 <= response.status_code < 300

        return {
            "status": "success" if is_success else "failed",
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "error_message": None if is_success else f"HTTP {response.status_code}",
        }

    except httpx.TimeoutException:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "status": "failed",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Request timeout setelah {timeout_seconds} detik",
        }

    except httpx.ConnectError as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "status": "failed",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Gagal terhubung ke server: {str(e)}",
        }

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "status": "failed",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": f"Error tak terduga: {str(e)}",
        }