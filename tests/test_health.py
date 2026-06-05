# /tests/test_health.py
"""Integration health checks — requires services to be running (make up).
URLs default to localhost for host-side runs; override via env for container-side.
"""
import os
import httpx
import pytest

BACKEND  = os.getenv("TEST_BACKEND_URL",  "http://localhost:8000")
CHANNELS = os.getenv("TEST_CHANNELS_URL", "http://localhost:8001")
FRONTEND = os.getenv("TEST_FRONTEND_URL", "http://localhost:3000")


def test_backend_health():
    r = httpx.get(f"{BACKEND}/health", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "ok"
    assert body["redis"] == "ok"
    assert body["db"] == "ok"


def test_channels_health():
    r = httpx.get(f"{CHANNELS}/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("channels") == "ok"


def test_frontend_up():
    r = httpx.get(FRONTEND, timeout=5)
    # Vite dev server may return 403 for cross-host requests from inside Docker,
    # but any non-5xx response confirms the service is running.
    assert r.status_code < 500


def test_metrics_shape():
    r = httpx.get(f"{BACKEND}/api/metrics", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "active_sessions" in body
    assert "tickets" in body
    assert "messages_by_channel" in body
    assert "sentiment_stats" in body
    assert "recent_tickets" in body


def test_copilot_shape():
    r = httpx.get(f"{BACKEND}/api/copilot", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "suggestions" in body
    assert isinstance(body["suggestions"], list)
