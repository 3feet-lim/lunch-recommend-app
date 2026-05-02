from __future__ import annotations

import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.routers import slack
from app.services.slack_signature import build_test_signature

SECRET = "test-secret"


def make_client(monkeypatch) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        slack_signing_secret=SECRET, environment="test"
    )
    return TestClient(app)


def signed_headers(body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    return {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": build_test_signature(SECRET, timestamp, body),
    }


def test_health_endpoint(monkeypatch) -> None:
    client = make_client(monkeypatch)
    assert client.get("/health").json() == {"status": "ok"}


def test_lunch_command_acknowledges_before_background_work(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_process(payload, settings) -> None:  # noqa: ANN001
        calls.append(payload.text)

    monkeypatch.setattr(slack, "process_lunch_command", fake_process)
    client = make_client(monkeypatch)
    body = urlencode(
        {
            "team_id": "T1",
            "channel_id": "C1",
            "user_id": "U1",
            "command": "/lunch",
            "text": "강남역 4명 팀점심",
            "response_url": "https://hooks.slack.test/secret",
        }
    ).encode()

    response = client.post("/slack/commands/lunch", content=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert "잠시만" in response.json()["text"]
    assert calls == ["강남역 4명 팀점심"]


def test_lunch_command_rejects_invalid_signature(monkeypatch) -> None:
    client = make_client(monkeypatch)
    body = b"text=hello"
    response = client.post(
        "/slack/commands/lunch",
        content=body,
        headers={"X-Slack-Request-Timestamp": str(int(time.time())), "X-Slack-Signature": "v0=bad"},
    )
    assert response.status_code == 401


def test_slack_retry_is_acknowledged_without_duplicate_background_work(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_process(payload, settings) -> None:  # noqa: ANN001
        calls.append(payload.text)

    monkeypatch.setattr(slack, "process_lunch_command", fake_process)
    client = make_client(monkeypatch)
    body = urlencode(
        {
            "team_id": "T1",
            "channel_id": "C1",
            "user_id": "U1",
            "text": "강남역 4명",
            "response_url": "https://hooks.slack.test/secret",
        }
    ).encode()
    headers = signed_headers(body) | {"X-Slack-Retry-Num": "1"}

    response = client.post("/slack/commands/lunch", content=body, headers=headers)

    assert response.status_code == 200
    assert "처리 중" in response.json()["text"]
    assert calls == []


def test_interactions_verify_signature(monkeypatch) -> None:
    client = make_client(monkeypatch)
    body = b"payload=%7B%7D"
    response = client.post("/slack/interactions", content=body, headers=signed_headers(body))
    assert response.status_code == 200
