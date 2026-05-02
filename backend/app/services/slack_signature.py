from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass

SLACK_SIGNATURE_VERSION = "v0"
DEFAULT_REPLAY_WINDOW_SECONDS = 60 * 5


class SlackSignatureError(ValueError):
    """Raised when a Slack request signature fails verification."""


@dataclass(frozen=True)
class SignatureVerificationResult:
    ok: bool
    reason: str | None = None


class SlackSignatureVerifier:
    """Verifies Slack request signatures against the exact raw request body."""

    def __init__(
        self,
        signing_secret: str | None,
        replay_window_seconds: int = DEFAULT_REPLAY_WINDOW_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.signing_secret = signing_secret or ""
        self.replay_window_seconds = replay_window_seconds
        self._now = now or time.time

    def verify(
        self,
        *,
        raw_body: bytes,
        timestamp: str | None,
        signature: str | None,
    ) -> SignatureVerificationResult:
        if not self.signing_secret:
            return SignatureVerificationResult(False, "missing_signing_secret")
        if not timestamp or not signature:
            return SignatureVerificationResult(False, "missing_signature_headers")

        try:
            request_timestamp = int(timestamp)
        except ValueError:
            return SignatureVerificationResult(False, "invalid_timestamp")

        if abs(int(self._now()) - request_timestamp) > self.replay_window_seconds:
            return SignatureVerificationResult(False, "stale_timestamp")

        expected = build_test_signature(self.signing_secret, timestamp, raw_body)
        if not hmac.compare_digest(expected, signature):
            return SignatureVerificationResult(False, "invalid_signature")
        return SignatureVerificationResult(True)


def build_test_signature(secret: str, timestamp: str, raw_body: bytes) -> str:
    """Build a Slack v0 signature for tests and local smoke checks."""

    base = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
    digest = hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return f"{SLACK_SIGNATURE_VERSION}={digest}"


def verify_slack_signature(
    *,
    signing_secret: str | None,
    timestamp: str | None,
    signature: str | None,
    raw_body: bytes,
    now: int | float | Callable[[], float] | None = None,
    require_secret: bool = True,
) -> None:
    """Fail closed unless the Slack signature is valid for the exact raw body."""

    if not signing_secret and not require_secret:
        return

    now_func: Callable[[], float] | None
    if callable(now):
        now_func = now
    elif now is None:
        now_func = None
    else:
        now_func = lambda: float(now)

    result = SlackSignatureVerifier(signing_secret, now=now_func).verify(
        raw_body=raw_body,
        timestamp=timestamp,
        signature=signature,
    )
    if not result.ok:
        raise SlackSignatureError(result.reason or "invalid_signature")
