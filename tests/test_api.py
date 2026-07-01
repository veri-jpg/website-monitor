"""
Integrasi test untuk endpoint API.
Menggunakan TestClient (HTTPX) dengan SQLite in-memory via fixture di conftest.py.
"""

import pytest


# ─── Health check ─────────────────────────────────────────────────────────────

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Websites CRUD ────────────────────────────────────────────────────────────

class TestWebsitesCRUD:
    def test_create_website_http(self, client):
        payload = {"name": "Test Site", "url": "https://example.com", "check_method": "http", "interval_seconds": 60}
        resp = client.post("/websites/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Site"
        assert data["id"] is not None
        # credentials tidak boleh ada di response
        assert "credentials" not in data

    def test_list_websites(self, client):
        client.post("/websites/", json={"name": "A", "url": "https://a.com", "check_method": "http", "interval_seconds": 60})
        client.post("/websites/", json={"name": "B", "url": "https://b.com", "check_method": "http", "interval_seconds": 60})
        resp = client.get("/websites/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_website_not_found(self, client):
        resp = client.get("/websites/9999")
        assert resp.status_code == 404

    def test_update_website_partial(self, client):
        resp = client.post("/websites/", json={"name": "Old", "url": "https://old.com", "check_method": "http", "interval_seconds": 60})
        wid = resp.json()["id"]
        resp = client.patch(f"/websites/{wid}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"
        assert resp.json()["url"] == "https://old.com"

    def test_delete_website(self, client):
        resp = client.post("/websites/", json={"name": "Del", "url": "https://del.com", "check_method": "http", "interval_seconds": 60})
        wid = resp.json()["id"]
        resp = client.delete(f"/websites/{wid}")
        assert resp.status_code == 204
        assert client.get(f"/websites/{wid}").status_code == 404

    def test_create_website_with_credentials_not_exposed(self, client):
        payload = {
            "name": "Secure Site",
            "url": "https://example.com/login",
            "check_method": "playwright",
            "interval_seconds": 120,
            "credentials": {"username": "admin", "password": "s3cret"},
        }
        resp = client.post("/websites/", json=payload)
        assert resp.status_code == 201
        assert "credentials" not in resp.json()

    def test_delete_nonexistent_website(self, client):
        resp = client.delete("/websites/9999")
        assert resp.status_code == 404


# ─── Check Results ────────────────────────────────────────────────────────────

class TestCheckResults:
    def test_list_check_results_empty(self, client):
        resp = client.get("/check-results/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_check_result_not_found(self, client):
        resp = client.get("/check-results/9999")
        assert resp.status_code == 404


# ─── Notification Rules ───────────────────────────────────────────────────────

class TestNotificationRules:
    def _create_website(self, client):
        resp = client.post("/websites/", json={"name": "W", "url": "https://w.com", "check_method": "http", "interval_seconds": 60})
        return resp.json()["id"]

    def test_create_notification_rule(self, client):
        wid = self._create_website(client)
        payload = {"website_id": wid, "channel": "telegram", "target": "12345", "retry_count": 3, "retry_delay_seconds": 30}
        resp = client.post("/notification-rules/", json=payload)
        assert resp.status_code == 201
        assert resp.json()["channel"] == "telegram"

    def test_create_rule_for_nonexistent_website(self, client):
        payload = {"website_id": 9999, "channel": "telegram", "target": "12345", "retry_count": 3, "retry_delay_seconds": 30}
        resp = client.post("/notification-rules/", json=payload)
        assert resp.status_code == 404

    def test_list_rules_filtered_by_website(self, client):
        wid = self._create_website(client)
        client.post("/notification-rules/", json={"website_id": wid, "channel": "telegram", "target": "aaa", "retry_count": 1, "retry_delay_seconds": 10})
        client.post("/notification-rules/", json={"website_id": wid, "channel": "email", "target": "x@x.com", "retry_count": 1, "retry_delay_seconds": 10})
        resp = client.get(f"/notification-rules/?website_id={wid}")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_delete_rule(self, client):
        wid = self._create_website(client)
        resp = client.post("/notification-rules/", json={"website_id": wid, "channel": "email", "target": "x@x.com", "retry_count": 1, "retry_delay_seconds": 10})
        rid = resp.json()["id"]
        assert client.delete(f"/notification-rules/{rid}").status_code == 204
        assert client.get(f"/notification-rules/{rid}").status_code == 404


# ─── API Key Auth ─────────────────────────────────────────────────────────────

class TestApiKeyAuth:
    def test_no_key_required_when_api_key_empty(self, client):
        # conftest menetapkan API_KEY="" sehingga auth dinonaktifkan
        resp = client.get("/websites/")
        assert resp.status_code == 200

    def test_rejects_wrong_key_when_api_key_set(self, client, monkeypatch):
        from app import config
        monkeypatch.setattr(config.settings, "api_key", "correct-key")
        resp = client.get("/websites/", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_accepts_correct_key(self, client, monkeypatch):
        from app import config
        monkeypatch.setattr(config.settings, "api_key", "correct-key")
        resp = client.get("/websites/", headers={"X-API-Key": "correct-key"})
        assert resp.status_code == 200
