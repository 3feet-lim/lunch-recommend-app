from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable

SLACK_SIGNATURE_VERSION = "v0"
DEFAULT_REPLAY_WINDOW_SECONDS = 60 * 5


class SlackSignatureError(ValueError):
    """Raised when Slack request signature verification fails."""


def build_test_signature(signing_secret: str, timestamp: str, raw_body: bytes) -> str:
    """Build a Slack-compatible signature for tests and local smoke fixtures."""
    base = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
    return (
        f"{SLACK_SIGNATURE_VERSION}="
        + hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    )


def verify_slack_signature(
    *,
    signing_secret: str | None,
    timestamp: str | None,
    signature: str | None,
    raw_body: bytes,
    now: int | float | None = None,
    replay_window_seconds: int = DEFAULT_REPLAY_WINDOW_SECONDS,
    require_secret: bool = True,
) -> None:
    """Verify Slack signature against the exact raw request body.

    Raises SlackSignatureError on every failure so callers fail closed.
    """
    if not signing_secret:
        if require_secret:
            raise SlackSignatureError("missing_signing_secret")
        return
    if not timestamp or not signature:
        raise SlackSignatureError("missing_signature_headers")

    try:
        request_timestamp = int(timestamp)
    except ValueError as exc:
        raise SlackSignatureError("invalid_timestamp") from exc

    current_time = int(time.time() if now is None else now)
    if abs(current_time - request_timestamp) > replay_window_seconds:
        raise SlackSignatureError("stale_timestamp")

    expected = build_test_signature(signing_secret, timestamp, raw_body)
    if not hmac.compare_digest(expected, signature):
        raise SlackSignatureError("invalid_signature")


class SlackSignatureVerifier:
    """Object wrapper for dependency injection-friendly signature verification."""

    def __init__(
        self,
        signing_secret: str | None,
        replay_window_seconds: int = DEFAULT_REPLAY_WINDOW_SECONDS,
        now: Callable[[], int | float] | None = None,
    ) -> None:
        self.signing_secret = signing_secret
        self.replay_window_seconds = replay_window_seconds
        self._now = now

    def verify(
        self,
        *,
        raw_body: bytes,
        timestamp: str | None,
        signature: str | None,
    ) -> None:
        verify_slack_signature(
            signing_secret=self.signing_secret,
            timestamp=timestamp,
            signature=signature,
            raw_body=raw_body,
            now=self._now() if self._now else None,
            replay_window_seconds=self.replay_window_seconds,
        )
