"""Slack-friendly Korean message formatting for lunch recommendations."""

from __future__ import annotations

import re
from typing import Any

from app.models.domain import WeatherCategory, WeatherContext
from app.services.recommendation_engine import Recommendation

_SECRET_PATTERNS = [
    re.compile(r"https://hooks\.slack\.com/services/[^\s)]+"),
    re.compile(r"xox[baprs]-[^\s)]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret)=([^\s&]+)"),
]


class MessageFormatter:
    """Build concise Slack response text without leaking sensitive values."""

    def missing_region_prompt(self) -> dict[str, str]:
        return _ephemeral("어느 지역에서 점심을 찾을까요? 예: `강남역 4명 팀점심`")

    def missing_party_size_prompt(self, region: str | None = None) -> dict[str, str]:
        prefix = f"{region}에서 " if region else ""
        return _ephemeral(f"{prefix}몇 명이 함께 가나요? 예: `4명`")

    def format_recommendations(
        self,
        recommendations: list[Recommendation] | list[dict[str, Any]],
        *,
        region: str,
        party_size: int,
        weather: WeatherContext | None = None,
        strict_radius_meters: int = 150,
    ) -> dict[str, str]:
        if not recommendations:
            return self.format_no_results(region=region, strict_radius_meters=strict_radius_meters)

        header = f"{region} 근처 {party_size}명 점심 추천이에요."
        lines = [header]
        if len(recommendations) < 3:
            lines.append(f"엄격한 {strict_radius_meters}m 범위에서 {len(recommendations)}곳만 찾았어요.")
        if weather is not None and not weather.is_available:
            lines.append("날씨 정보는 사용할 수 없어 요일/요청 맥락 중심으로 골랐어요.")

        for index, item in enumerate(recommendations[:3], start=1):
            lines.append(_format_recommendation_line(index, item))
        return _ephemeral("\n".join(lines))

    def format_no_results(self, *, region: str, strict_radius_meters: int = 150) -> dict[str, str]:
        return _ephemeral(
            f"{region} 기준 {strict_radius_meters}m 안에서 음식점을 찾지 못했어요. "
            "범위를 임의로 넓히지 않았으니 더 구체적인 위치로 다시 요청해 주세요."
        )

    def format_region_not_found(self, region: str | None = None) -> dict[str, str]:
        target = f" `{region}`" if region else ""
        return _ephemeral(f"지역{target}을 찾지 못했어요. 역명이나 건물명처럼 더 구체적으로 알려주세요.")

    def format_error(self, message: str | Exception | None = None) -> dict[str, str]:
        safe_detail = _sanitize(str(message or ""))
        suffix = f" ({safe_detail})" if safe_detail else ""
        return _ephemeral(f"점심 추천을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.{suffix}")

    # Compatibility names for callers/tests.
    error_message = format_error
    recommendations = format_recommendations


def _format_recommendation_line(index: int, item: Recommendation | dict[str, Any]) -> str:
    name = _field(item, "name") or "이름 없는 음식점"
    category = _field(item, "category") or "음식점"
    distance = _field(item, "distance_meters", "distance")
    address = _field(item, "address", "road_address", "address_name", "road_address_name")
    map_url = _field(item, "map_url", "place_url")
    reason = _field(item, "reason") or "가까운 실제 음식점"

    details = [category]
    if distance:
        details.append(f"{distance}m")
    if address:
        details.append(address)
    if map_url:
        details.append(map_url)
    return f"{index}. *{name}* — {' · '.join(details)}\n   이유: {reason}"


def _field(item: Recommendation | dict[str, Any], *names: str) -> str | None:
    for name in names:
        if isinstance(item, dict):
            value = item.get(name)
        else:
            value = getattr(item, name, None)
        if value not in (None, ""):
            return str(value)
    return None


def _sanitize(value: str) -> str:
    cleaned = value.replace("Traceback", "")
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[redacted]", cleaned)
    return cleaned.strip()[:160]


def _ephemeral(text: str) -> dict[str, str]:
    return {"response_type": "ephemeral", "text": text}


def format_missing_region_prompt() -> dict[str, str]:
    return MessageFormatter().missing_region_prompt()


def format_missing_party_size_prompt(region: str | None = None) -> dict[str, str]:
    return MessageFormatter().missing_party_size_prompt(region)
