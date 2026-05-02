"""Shared pytest guardrails for Slack lunch bot tests.

The suite must be safe to run on developer machines and CI without credentials.
It blocks real outbound sockets by default; tests should use FastAPI TestClient,
httpx mock transports, monkeypatch fakes, or in-memory stores instead.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import socket
import time
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def fake_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide fake credentials so tests never require real secrets."""

    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-slack-signing-secret")
    monkeypatch.setenv("NAVER_GEOCODING_CLIENT_ID", "test-naver-id")
    monkeypatch.setenv("NAVER_GEOCODING_CLIENT_SECRET", "test-naver-secret")
    monkeypatch.setenv("KAKAO_REST_API_KEY", "test-kakao-key")
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-openweather-key")
    monkeypatch.setenv("DEFAULT_TIMEZONE", "Asia/Seoul")
    monkeypatch.setenv("RESTAURANT_SEARCH_RADIUS_METERS", "150")
    monkeypatch.setenv("CONVERSATION_TTL_MINUTES", "30")
    monkeypatch.setenv("UPSTREAM_TIMEOUT_SECONDS", "3")


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail tests that try to open real network sockets.

    This intentionally catches accidental requests/httpx client usage that is not
    backed by a mock transport. In-process ASGI tests should not need sockets.
    """

    original_socket = socket.socket

    class GuardedSocket(original_socket):  # type: ignore[misc, valid-type]
        def connect(self, address):  # type: ignore[no-untyped-def]
            raise AssertionError(f"real network access blocked in tests: {address!r}")

        def connect_ex(self, address):  # type: ignore[no-untyped-def]
            raise AssertionError(f"real network access blocked in tests: {address!r}")

    def blocked_create_connection(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"real network access blocked in tests: {args!r} {kwargs!r}")

    monkeypatch.setattr(socket, "socket", GuardedSocket)
    monkeypatch.setattr(socket, "create_connection", blocked_create_connection)
    yield


@pytest.fixture
def slack_signing_secret() -> str:
    return os.environ["SLACK_SIGNING_SECRET"]


def slack_signature(secret: str, raw_body: bytes, timestamp: int | None = None) -> tuple[str, str]:
    """Return Slack-compatible timestamp and v0 signature for a raw body."""

    ts = str(timestamp if timestamp is not None else int(time.time()))
    base = b"v0:" + ts.encode() + b":" + raw_body
    digest = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return ts, f"v0={digest}"


@pytest.fixture
def signed_slack_headers(slack_signing_secret: str):
    def build(raw_body: bytes, timestamp: int | None = None) -> dict[str, str]:
        ts, sig = slack_signature(slack_signing_secret, raw_body, timestamp)
        return {
            "content-type": "application/x-www-form-urlencoded",
            "x-slack-request-timestamp": ts,
            "x-slack-signature": sig,
        }

    return build
