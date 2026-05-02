import hashlib
import hmac
import time
from dataclasses import dataclass

SLACK_SIGNATURE_VERSION = "v0"
DEFAULT_REPLAY_WINDOW_SECONDS = 60 * 5


@dataclass(frozen=True)
class SignatureVerificationResult:
    ok: bool
    reason: str | None = None


class SlackSignatureVerifier:
    """Verifies Slack request signatures against the exact raw request body."""

    def __init__(
        self,
        signing_secret: str,
        replay_window_seconds: int = DEFAULT_REPLAY_WINDOW_SECONDS,
        now: callable | None = None,
    ) -> None:
        self.signing_secret = signing_secret
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

        base = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
        expected = (
            f"{SLACK_SIGNATURE_VERSION}="
            + hmac.new(
                self.signing_secret.encode("utf-8"), base, hashlib.sha256
            ).hexdigest()
        )
        if not hmac.compare_digest(expected, signature):
            return SignatureVerificationResult(False, "invalid_signature")
        return SignatureVerificationResult(True)
