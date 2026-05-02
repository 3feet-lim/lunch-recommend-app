"""Explainable rule-based restaurant ranking for the Slack lunch MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.domain import RestaurantCandidate, WeatherCategory, WeatherContext


@dataclass(frozen=True, slots=True)
class Recommendation:
    name: str
    category: str
    distance_meters: int | None
    address: str | None
    map_url: str | None
    reason: str
    score: float
    restaurant: RestaurantCandidate | dict[str, Any]


class RecommendationEngine:
    """Rank real provider candidates without radius expansion or synthesis."""

    def recommend(
        self,
        restaurants: list[RestaurantCandidate] | list[dict[str, Any]],
        *,
        weather: WeatherContext | WeatherCategory | str | None = None,
        weekday: str | bool | None = None,
        party_size: int | None = None,
        context: str | None = None,
        now: datetime | None = None,
        limit: int = 3,
    ) -> list[Recommendation]:
        weather_category = _weather_category(weather)
        is_weekday = _is_weekday(weekday, now)
        scored = [
            self._score_candidate(candidate, weather_category, is_weekday, party_size, context, index)
            for index, candidate in enumerate(restaurants)
        ]
        scored.sort(key=lambda item: (-item.score, _distance_sort_value(item), item.name))
        return scored[: max(0, min(limit, 3))]

    def _score_candidate(
        self,
        candidate: RestaurantCandidate | dict[str, Any],
        weather: WeatherCategory | None,
        is_weekday: bool,
        party_size: int | None,
        context: str | None,
        index: int,
    ) -> Recommendation:
        name = _field(candidate, "name", "place_name") or f"식당 {index + 1}"
        category = _field(candidate, "category", "category_name") or "음식점"
        distance = _int_field(candidate, "distance_meters", "distance")
        address = _field(candidate, "road_address", "road_address_name") or _field(
            candidate, "address", "address_name"
        )
        map_url = _field(candidate, "map_url", "place_url")

        score = 100.0
        reasons: list[str] = []
        if distance is not None:
            score += max(0.0, 150.0 - float(distance)) / 10.0
            reasons.append(f"{distance}m 거리")

        category_text = category.lower()
        if weather in {WeatherCategory.RAIN, WeatherCategory.SNOW, WeatherCategory.COLD}:
            if any(term in category_text for term in ("한식", "국", "탕", "찌개", "분식", "일식")):
                score += 12.0
                reasons.append("날씨에 어울리는 따뜻한 메뉴")
            else:
                reasons.append("날씨를 고려한 가까운 선택")
        elif weather in {WeatherCategory.HOT, WeatherCategory.CLEAR}:
            if any(term in category_text for term in ("냉", "면", "카페", "샐러드", "분식")):
                score += 8.0
                reasons.append("맑거나 더운 날에 부담 적은 메뉴")

        if is_weekday:
            score += 4.0
            reasons.append("평일 점심에 빠르게 이동 가능")
        else:
            reasons.append("주말에도 편하게 고를 수 있음")

        if party_size is not None:
            if party_size >= 4:
                if any(term in category_text for term in ("한식", "고기", "중식", "뷔페", "식당")):
                    score += 10.0
                reasons.append(f"{party_size}명 모임에 적합")
            else:
                reasons.append(f"{party_size}명이 가볍게 방문 가능")

        normalized_context = (context or "").strip()
        if normalized_context:
            if any(term in normalized_context for term in ("팀", "동료", "회식")):
                score += 5.0
                reasons.append("팀 점심 맥락 반영")
            elif any(term in normalized_context for term in ("혼밥", "혼자")):
                score += 3.0
                reasons.append("간단한 식사 맥락 반영")
            else:
                reasons.append("요청 맥락 반영")

        if not reasons:
            reasons.append("가까운 실제 음식점")

        return Recommendation(
            name=name,
            category=category,
            distance_meters=distance,
            address=address,
            map_url=map_url,
            reason=" · ".join(dict.fromkeys(reasons[:3])),
            score=score,
            restaurant=candidate,
        )


def _weather_category(weather: WeatherContext | WeatherCategory | str | None) -> WeatherCategory | None:
    if isinstance(weather, WeatherContext):
        return weather.category
    if isinstance(weather, WeatherCategory):
        return weather
    if isinstance(weather, str):
        try:
            return WeatherCategory(weather.lower())
        except ValueError:
            return None
    return None


def _is_weekday(weekday: str | bool | None, now: datetime | None) -> bool:
    if isinstance(weekday, bool):
        return weekday
    if isinstance(weekday, str):
        return weekday.lower() not in {"weekend", "sat", "sun", "토", "일", "주말"}
    return (now or datetime.now()).weekday() < 5


def _distance_sort_value(item: Recommendation) -> int:
    return item.distance_meters if item.distance_meters is not None else 999_999


def _field(candidate: RestaurantCandidate | dict[str, Any], *names: str) -> str | None:
    for name in names:
        if isinstance(candidate, dict):
            value = candidate.get(name)
        else:
            value = getattr(candidate, name, None)
        if value not in (None, ""):
            return str(value)
    return None


def _int_field(candidate: RestaurantCandidate | dict[str, Any], *names: str) -> int | None:
    value = _field(candidate, *names)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
