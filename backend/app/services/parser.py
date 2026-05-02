"""Korean Slack lunch command parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PARTY_SIZE_RE = re.compile(r"(?P<size>\d{1,2})\s*(?:명|인|people|persons?)\b", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ParsedLunchRequest:
    """Structured fields extracted from a `/lunch` text payload."""

    region: str | None
    party_size: int | None
    companion_context: str | None
    original_text: str

    @property
    def is_complete(self) -> bool:
        return bool(self.region) and self.party_size is not None


def parse_slash_command_text(text: str | None) -> ParsedLunchRequest:
    """Parse region, Korean party size, and optional context from free text.

    The MVP intentionally keeps parsing deterministic: the first token before a
    party-size expression is the region, and remaining text is optional context.
    Examples: ``강남역 4명 팀점심`` -> region ``강남역``, party size ``4``.
    """

    normalized = _normalize_text(text)
    if not normalized:
        return ParsedLunchRequest(
            region=None,
            party_size=None,
            companion_context=None,
            original_text="",
        )

    match = _PARTY_SIZE_RE.search(normalized)
    if match is None:
        return ParsedLunchRequest(
            region=normalized or None,
            party_size=None,
            companion_context=None,
            original_text=normalized,
        )

    party_size = int(match.group("size"))
    before = normalized[: match.start()].strip()
    after = normalized[match.end() :].strip()
    region = before or None
    context = after or None
    return ParsedLunchRequest(
        region=region,
        party_size=party_size,
        companion_context=context,
        original_text=normalized,
    )


# Compatibility aliases used by contract tests and older route code.
parse_lunch_text = parse_slash_command_text
parse_command_text = parse_slash_command_text


def merge_pending_response(
    current: ParsedLunchRequest,
    *,
    pending_question: str | None,
    response_text: str | None,
) -> ParsedLunchRequest:
    """Merge a follow-up answer into an existing parsed request."""

    response = parse_slash_command_text(response_text)
    if pending_question == "region":
        region = response.region or _normalize_text(response_text) or current.region
        return ParsedLunchRequest(
            region=region,
            party_size=response.party_size or current.party_size,
            companion_context=response.companion_context or current.companion_context,
            original_text=response.original_text or current.original_text,
        )
    if pending_question == "party_size":
        return ParsedLunchRequest(
            region=current.region or response.region,
            party_size=(
                response.party_size
                or _parse_bare_party_size(response_text)
                or current.party_size
            ),
            companion_context=response.companion_context or current.companion_context,
            original_text=response.original_text or current.original_text,
        )
    return response


def next_missing_question(parsed: ParsedLunchRequest) -> str | None:
    """Return the next required prompt field for the missing-info flow."""

    if not parsed.region:
        return "region"
    if parsed.party_size is None:
        return "party_size"
    return None


def _parse_bare_party_size(text: str | None) -> int | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if normalized.isdecimal():
        return int(normalized)
    match = _PARTY_SIZE_RE.search(normalized)
    return int(match.group("size")) if match else None


def _normalize_text(text: str | None) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "").strip())
