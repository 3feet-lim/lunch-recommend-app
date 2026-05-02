from __future__ import annotations

import pytest

from app.services.slack_signature import (
    SlackSignatureError,
    build_test_signature,
    verify_slack_signature,
)


def test_valid_slack_signature_uses_raw_body() -> None:
    body = b"text=%EA%B0%95%EB%82%A8%EC%97%AD+4%EB%AA%85&response_url=https%3A%2F%2Fhooks.slack.test%2Fsecret"
    timestamp = "1000"
    secret = "test-secret"
    signature = build_test_signature(secret, timestamp, body)

    verify_slack_signature(
        signing_secret=secret,
        timestamp=timestamp,
        signature=signature,
        raw_body=body,
        now=1000,
    )

    reparsed_body = b"response_url=https%3A%2F%2Fhooks.slack.test%2Fsecret&text=%EA%B0%95%EB%82%A8%EC%97%AD+4%EB%AA%85"
    with pytest.raises(SlackSignatureError):
        verify_slack_signature(
            signing_secret=secret,
            timestamp=timestamp,
            signature=signature,
            raw_body=reparsed_body,
            now=1000,
        )


def test_invalid_and_stale_signatures_fail_closed() -> None:
    body = b"text=hello"
    secret = "test-secret"

    with pytest.raises(SlackSignatureError):
        verify_slack_signature(
            signing_secret=secret,
            timestamp="1000",
            signature="v0=bad",
            raw_body=body,
            now=1000,
        )

    signature = build_test_signature(secret, "1000", body)
    with pytest.raises(SlackSignatureError):
        verify_slack_signature(
            signing_secret=secret,
            timestamp="1000",
            signature=signature,
            raw_body=body,
            now=2000,
        )


def test_missing_signing_secret_fails_when_required() -> None:
    with pytest.raises(SlackSignatureError):
        verify_slack_signature(
            signing_secret=None,
            timestamp="1000",
            signature="v0=anything",
            raw_body=b"text=hello",
            now=1000,
            require_secret=True,
        )
