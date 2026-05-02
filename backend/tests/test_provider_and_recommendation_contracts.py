"""Provider, recommendation, and formatting contracts from the test spec."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract
BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"


def _import_or_skip(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.skip(f"{module_name} is not present yet: {exc}")


def test_kakao_restaurant_client_source_preserves_strict_150m_fd6_contract() -> None:
    source = APP_ROOT / "services" / "restaurant_search_kakao.py"
    if not source.exists():
        pytest.skip("Kakao restaurant client is not present yet")

    text = source.read_text(encoding="utf-8")
    assert "category_group_code" in text
    assert "FD6" in text
    assert "radius" in text
    assert "150" in text
    assert "sort" in text and "distance" in text


def test_recommendation_engine_does_not_expand_or_synthesize_results() -> None:
    module = _import_or_skip("app.services.recommendation_engine")
    engine_type = getattr(module, "RecommendationEngine", None)
    if engine_type is None:
        raise AssertionError("RecommendationEngine class is required")

    # This behavioral check is intentionally duck-typed so implementation can use
    # dataclasses, Pydantic models, or dictionaries for restaurants.
    restaurants = [
        {
            "id": "r1",
            "name": "A",
            "category": "한식",
            "distance_meters": 20,
            "address": "a",
            "place_url": "https://map.example/a",
        },
        {
            "id": "r2",
            "name": "B",
            "category": "분식",
            "distance_meters": 50,
            "address": "b",
            "place_url": "https://map.example/b",
        },
    ]
    engine = engine_type()
    recommend = getattr(engine, "recommend", None)
    if not callable(recommend):
        raise AssertionError("RecommendationEngine.recommend is required")

    try:
        results = recommend(
            restaurants, weather="rain", weekday="weekday", party_size=4, context="팀점심"
        )
    except TypeError:
        results = recommend(
            restaurants=restaurants,
            weather="rain",
            weekday="weekday",
            party_size=4,
            context="팀점심",
        )

    assert len(results) <= 2
    names = [
        getattr(item, "name", None) if not isinstance(item, dict) else item.get("name")
        for item in results
    ]
    assert set(names).issubset({"A", "B"})


def test_message_formatter_hides_sensitive_values() -> None:
    module = _import_or_skip("app.services.message_formatter")
    formatter_type = getattr(module, "MessageFormatter", None)
    if formatter_type is None:
        pytest.skip("MessageFormatter class is not present yet")

    formatter = formatter_type()
    error_func = getattr(formatter, "format_error", None) or getattr(
        formatter, "error_message", None
    )
    if not callable(error_func):
        raise AssertionError("MessageFormatter must expose an error formatting method")

    message = str(
        error_func("failed with https://hooks.slack.com/services/T/B/SECRET and xoxb-secret-token")
    )
    assert "hooks.slack.com/services" not in message
    assert "xoxb-" not in message
    assert "Traceback" not in message
