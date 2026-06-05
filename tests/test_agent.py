# /tests/test_agent.py
"""Integration tests for the agent message endpoint — requires services running."""
import httpx
import pytest

BACKEND = "http://localhost:8000"


def _post_message(text: str, channel: str = "webchat", session_id: str | None = None) -> dict:
    payload = {
        "session_id": session_id or f"{channel}_test_001",
        "channel": channel,
        "user_id": "test_001",
        "text": text,
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/message", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def test_agent_responds():
    body = _post_message("Hello, I need help with my electricity bill.")
    assert "text" in body
    assert len(body["text"]) > 5
    assert body["session_id"].startswith("webchat")


def test_agent_returns_sentiment():
    body = _post_message("This is terrible, my power has been out for 3 days!")
    assert body.get("sentiment") in ("positive", "neutral", "negative")


def test_agent_arabic():
    body = _post_message("مرحباً، أحتاج مساعدة", channel="webchat", session_id="webchat_ar_test")
    assert len(body["text"]) > 5


def test_agent_ticket_creation():
    body = _post_message(
        "My electricity meter is broken and I need a repair, please create a ticket.",
        session_id="webchat_ticket_test",
    )
    # Ticket may or may not be created depending on agent decision
    assert "ticket_id" in body
    assert "escalate" in body


def test_session_history():
    session_id = "webchat_history_test"
    _post_message("First message for history test.", session_id=session_id)
    r = httpx.get(f"{BACKEND}/api/session/{session_id}", timeout=5)
    assert r.status_code == 200
    history = r.json()
    assert isinstance(history, list)
    assert any(h["role"] == "user" for h in history)
