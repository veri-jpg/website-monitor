"""
Unit test untuk logika core di scheduler/jobs.py.
Tidak membutuhkan database atau network — semua dependency di-mock.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.jobs import (
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY_SECONDS,
    _check_with_retry,
    _get_retry_config,
    _is_due_for_check,
)


def _make_website(is_checking=False, last_checked_at=None, interval_seconds=60, notification_rules=None):
    w = MagicMock()
    w.is_checking = is_checking
    w.last_checked_at = last_checked_at
    w.interval_seconds = interval_seconds
    w.notification_rules = notification_rules or []
    return w


# ─── _is_due_for_check ───────────────────────────────────────────────────────

class TestIsDueForCheck:
    def test_never_checked_is_due(self):
        w = _make_website(last_checked_at=None)
        assert _is_due_for_check(w, datetime.now(timezone.utc)) is True

    def test_currently_checking_is_not_due(self):
        w = _make_website(is_checking=True, last_checked_at=None)
        assert _is_due_for_check(w, datetime.now(timezone.utc)) is False

    def test_past_interval_is_due(self):
        last = datetime.now(timezone.utc) - timedelta(seconds=120)
        w = _make_website(last_checked_at=last, interval_seconds=60)
        assert _is_due_for_check(w, datetime.now(timezone.utc)) is True

    def test_within_interval_is_not_due(self):
        last = datetime.now(timezone.utc) - timedelta(seconds=30)
        w = _make_website(last_checked_at=last, interval_seconds=60)
        assert _is_due_for_check(w, datetime.now(timezone.utc)) is False

    def test_naive_datetime_treated_as_utc(self):
        # last_checked_at tanpa tzinfo (dari DB lama) tidak boleh crash
        last = datetime.utcnow() - timedelta(seconds=120)
        assert last.tzinfo is None
        w = _make_website(last_checked_at=last, interval_seconds=60)
        assert _is_due_for_check(w, datetime.now(timezone.utc)) is True


# ─── _get_retry_config ───────────────────────────────────────────────────────

class TestGetRetryConfig:
    def test_uses_rule_values_when_present(self):
        rule = MagicMock(retry_count=5, retry_delay_seconds=10)
        w = _make_website(notification_rules=[rule])
        assert _get_retry_config(w) == (5, 10)

    def test_uses_defaults_when_no_rules(self):
        w = _make_website(notification_rules=[])
        assert _get_retry_config(w) == (DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_SECONDS)


# ─── _check_with_retry ───────────────────────────────────────────────────────

class TestCheckWithRetry:
    @pytest.mark.asyncio
    async def test_returns_immediately_on_first_success(self):
        success_result = {"status": "success", "status_code": 200, "response_time_ms": 50, "error_message": None}
        with patch("app.scheduler.jobs._run_single_check", new=AsyncMock(return_value=success_result)):
            results = await _check_with_retry(1, "http", "http://example.com", None, None, 3, 0)
        assert len(results) == 1
        assert results[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_retries_on_failure_and_returns_all_attempts(self):
        fail = {"status": "failed", "status_code": None, "response_time_ms": 100, "error_message": "err"}
        with patch("app.scheduler.jobs._run_single_check", new=AsyncMock(return_value=fail)), \
             patch("app.scheduler.jobs.asyncio.sleep", new=AsyncMock()):
            results = await _check_with_retry(1, "http", "http://example.com", None, None, retry_count=2, retry_delay_seconds=0)
        # retry_count=2 berarti 1 percobaan awal + 2 retry = 3 total
        assert len(results) == 3
        assert all(r["status"] == "failed" for r in results)

    @pytest.mark.asyncio
    async def test_stops_retrying_after_success(self):
        fail = {"status": "failed", "status_code": None, "response_time_ms": 100, "error_message": "err"}
        success = {"status": "success", "status_code": 200, "response_time_ms": 50, "error_message": None}
        side_effects = [fail, success]
        with patch("app.scheduler.jobs._run_single_check", new=AsyncMock(side_effect=side_effects)), \
             patch("app.scheduler.jobs.asyncio.sleep", new=AsyncMock()):
            results = await _check_with_retry(1, "http", "http://example.com", None, None, retry_count=3, retry_delay_seconds=0)
        assert len(results) == 2
        assert results[-1]["status"] == "success"
