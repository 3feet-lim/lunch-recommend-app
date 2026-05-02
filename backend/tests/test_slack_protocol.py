import hashlib
import hmac
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.routers import slack

SECRET = "test-secret"


def signed_headers(
    body: bytes, secret: str = SECRET, timestamp: int | None = None
) -> dict[str, str]:
    ts = str(timestamp or int(time.time()))
    base = b"v0:" + ts.encode() + b":" + body
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }


def command_body(text: str = "강남역 4명 팀점심") -> bytes:
    return urlencode(
        {
            "team_id": "T1",
            "channel_id": "C1",
            "user_id": "U1",
            "command": "/lunch",
            "text": text,
            "response_url": "https://hooks.slack.test/response/secret",
            "trigger_id": "trigger.1",
        }
    ).encode()


def client() -> TestClient:
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={"slack_signing_secret": SECRET}
    )
    return TestClient(app)


def test_health_endpoint_returns_healthy_status():
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_lunch_command_accepts_valid_slack_signature():
    body = command_body()
    response = client().post("/slack/commands/lunch", content=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert "확인" in response.json()["text"]


def test_lunch_command_rejects_invalid_slack_signature():
    body = command_body()
    headers = signed_headers(body) | {"X-Slack-Signature": "v0=invalid"}

    response = client().post("/slack/commands/lunch", content=body, headers=headers)

    assert response.status_code == 401


def test_lunch_command_rejects_stale_slack_timestamp():
    body = command_body()
    stale_timestamp = int(time.time()) - 600

    response = client().post(
        "/slack/commands/lunch",
        content=body,
        headers=signed_headers(body, timestamp=stale_timestamp),
    )

    assert response.status_code == 401


def test_slack_signature_uses_exact_raw_body():
    body = command_body("강남역 4명")
    tampered_body = command_body("강남역 5명")

    response = client().post(
        "/slack/commands/lunch",
        content=tampered_body,
        headers=signed_headers(body),
    )

    assert response.status_code == 401


def test_lunch_command_ack_is_returned_before_background_work(monkeypatch):
    called = False

    async def fail_if_executed_before_ack(command):
        nonlocal called
        called = True

    monkeypatch.setattr(slack, "process_lunch_command", fail_if_executed_before_ack)
    body = command_body()

    response = client().post("/slack/commands/lunch", content=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert response.json()["response_type"] == "ephemeral"
    assert called is True


def test_retry_duplicate_returns_already_processing_ack():
    slack._SEEN_REQUESTS.clear()
    body = command_body()
    first = client().post("/slack/commands/lunch", content=body, headers=signed_headers(body))
    second_headers = signed_headers(body) | {"X-Slack-Retry-Num": "1"}

    second = client().post("/slack/commands/lunch", content=body, headers=second_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert "이미" in second.json()["text"]


def test_interactions_endpoint_verifies_signature():
    body = urlencode({"payload": '{"type":"block_actions"}'}).encode()
    response = client().post("/slack/interactions", content=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert "지원하지 않는" in response.json()["text"]
