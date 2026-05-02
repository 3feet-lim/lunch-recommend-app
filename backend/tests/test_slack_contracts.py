"""Behavior contracts for Slack request safety and MVP boundaries.

The tests skip while implementation modules are absent. Once worker lanes add the
specified modules, these become executable acceptance checks without real network.
"""

from __future__ import annotations

import importlib
import inspect
import time
from urllib.parse import urlencode

import pytest

pytestmark = pytest.mark.contract


def _import_or_skip(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.skip(f"{module_name} is not present yet: {exc}")


def _find_callable(module, *names: str):
    for name in names:
        func = getattr(module, name, None)
        if callable(func):
            return func
    available = [
        name for name, value in vars(module).items() if callable(value) and not name.startswith("_")
    ]
    raise AssertionError(f"expected one of {names}; available callables: {available}")


def _call_signature_verifier(
    func, *, secret: str, body: bytes, timestamp: str, signature: str
) -> bool:
    """Call the verifier using the documented contract or compatible names."""

    params = inspect.signature(func).parameters
    kwargs = {}
    aliases = {
        "signing_secret": secret,
        "secret": secret,
        "raw_body": body,
        "body": body,
        "timestamp": timestamp,
        "request_timestamp": timestamp,
        "slack_signature": signature,
        "signature": signature,
    }
    for name in params:
        if name in aliases:
            kwargs[name] = aliases[name]
    if len(kwargs) == len(params):
        result = func(**kwargs)
    else:
        result = func(secret, timestamp, body, signature)
    return bool(result)


def test_slack_signature_accepts_valid_raw_body_and_rejects_tampering(
    slack_signing_secret: str,
    signed_slack_headers,
) -> None:
    module = _import_or_skip("app.services.slack_signature")
    verifier = _find_callable(module, "verify_slack_signature", "is_valid_slack_signature")

    raw_body = urlencode(
        {"team_id": "T1", "channel_id": "C1", "user_id": "U1", "text": "강남역 4명"}
    ).encode()
    headers = signed_slack_headers(raw_body)

    assert _call_signature_verifier(
        verifier,
        secret=slack_signing_secret,
        body=raw_body,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )
    assert not _call_signature_verifier(
        verifier,
        secret=slack_signing_secret,
        body=raw_body + b"&text=tampered",
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )


def test_slack_signature_rejects_stale_timestamp(
    slack_signing_secret: str, signed_slack_headers
) -> None:
    module = _import_or_skip("app.services.slack_signature")
    verifier = _find_callable(module, "verify_slack_signature", "is_valid_slack_signature")

    raw_body = b"team_id=T1&channel_id=C1&user_id=U1&text=%EA%B0%95%EB%82%A8%EC%97%AD+4%EB%AA%85"
    stale_ts = int(time.time()) - 60 * 10
    headers = signed_slack_headers(raw_body, timestamp=stale_ts)

    assert not _call_signature_verifier(
        verifier,
        secret=slack_signing_secret,
        body=raw_body,
        timestamp=headers["x-slack-request-timestamp"],
        signature=headers["x-slack-signature"],
    )


def test_slash_parser_extracts_region_party_size_and_context() -> None:
    module = _import_or_skip("app.services.parser")
    parser = _find_callable(
        module, "parse_slash_command_text", "parse_lunch_text", "parse_command_text"
    )

    parsed = parser("강남역 4명 팀점심")
    region = (
        getattr(parsed, "region", None) if not isinstance(parsed, dict) else parsed.get("region")
    )
    party_size = (
        getattr(parsed, "party_size", None)
        if not isinstance(parsed, dict)
        else parsed.get("party_size")
    )
    context = (
        getattr(parsed, "companion_context", None)
        if not isinstance(parsed, dict)
        else parsed.get("companion_context")
    )

    assert region == "강남역"
    assert party_size == 4
    assert context in {"팀점심", "team lunch", "팀 점심"}
