from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.domain import RestaurantCandidate, WeatherContext
from app.services.conversation_state import ConversationState, ConversationStateStore, StateKey
from app.services.message_formatter import (
    format_missing_party_size_prompt,
    format_missing_region_prompt,
    format_no_restaurants,
    format_recommendations,
)
from app.services.parser import parse_lunch_text
from app.services.recommendation_engine import RecommendationEngine, RecommendationRequestContext


def test_parser_extracts_region_party_size_and_context_from_korean_text() -> None:
    parsed = parse_lunch_text("강남역 4명 팀점심")

    assert parsed.region == "강남역"
    assert parsed.party_size == 4
    assert parsed.companion_context == "팀점심"


def test_parser_treats_empty_text_as_missing_region_and_party_size() -> None:
    parsed = parse_lunch_text("   ")

    assert parsed.region is None
    assert parsed.party_size is None
    assert parsed.companion_context is None


def test_parser_region_without_party_size_preserves_region() -> None:
    parsed = parse_lunch_text("강남역")

    assert parsed.region == "강남역"
    assert parsed.party_size is None


def test_state_key_uses_team_channel_user() -> None:
    key = StateKey(team_id="T1", channel_id="C1", user_id="U1")

    assert key.value == "T1/C1/U1"


def test_sqlite_state_store_preserves_state_across_instances(tmp_path) -> None:
    db_path = tmp_path / "conversation.sqlite3"
    key = StateKey(team_id="T1", channel_id="C1", user_id="U1")
    expires_at = datetime.now(UTC) + timedelta(minutes=30)

    ConversationStateStore(db_path).upsert(
        key,
        ConversationState(
            pending_question="party_size",
            region="강남역",
            party_size=None,
            companion_context=None,
            response_url="https://hooks.slack.test/secret",
            expires_at=expires_at,
            last_request_fingerprint="abc",
        ),
    )

    restored = ConversationStateStore(db_path).get(key)

    assert restored is not None
    assert restored.pending_question == "party_size"
    assert restored.region == "강남역"
    assert restored.last_request_fingerprint == "abc"


def test_sqlite_state_store_ignores_expired_state(tmp_path) -> None:
    store = ConversationStateStore(tmp_path / "conversation.sqlite3")
    key = StateKey(team_id="T1", channel_id="C1", user_id="U1")

    store.upsert(
        key,
        ConversationState(
            pending_question="region",
            region=None,
            party_size=None,
            companion_context=None,
            response_url="https://hooks.slack.test/secret",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
            last_request_fingerprint=None,
        ),
    )

    assert store.get(key) is None


def test_recommendation_engine_returns_at_most_three_without_expanding_radius() -> None:
    restaurants = [
        RestaurantCandidate(
            id=str(index),
            name=f"식당 {index}",
            category="한식",
            distance_meters=index * 10,
            address="서울 강남구",
            place_url=f"https://place.test/{index}",
        )
        for index in range(1, 6)
    ]
    context = RecommendationRequestContext(
        party_size=4,
        companion_context="팀점심",
        weather=WeatherContext(condition="rain", available=True),
        is_weekend=False,
    )

    recommendations = RecommendationEngine().recommend(restaurants, context)

    assert len(recommendations) == 3
    assert {item.restaurant.id for item in recommendations}.issubset(
        {restaurant.id for restaurant in restaurants}
    )
    assert all(item.reason for item in recommendations)


def test_recommendation_engine_returns_fewer_than_three_when_only_two_exist() -> None:
    restaurants = [
        RestaurantCandidate(id="1", name="A", category="분식", distance_meters=50),
        RestaurantCandidate(id="2", name="B", category="일식", distance_meters=80),
    ]
    context = RecommendationRequestContext(party_size=1, is_weekend=True)

    recommendations = RecommendationEngine().recommend(restaurants, context)

    assert [item.restaurant.id for item in recommendations] == ["1", "2"]


def test_formatter_outputs_korean_prompts_and_strict_radius_message() -> None:
    assert "지역" in format_missing_region_prompt()["text"]
    assert "몇 명" in format_missing_party_size_prompt("강남역")["text"]
    assert "150m" in format_no_restaurants(150)["text"]


def test_formatter_includes_numbered_recommendations_and_weather_fallback_note() -> None:
    restaurants = [
        RestaurantCandidate(
            id="1",
            name="김치찌개집",
            category="한식",
            distance_meters=42,
            address="서울 강남구",
            place_url="https://place.test/1",
        )
    ]
    context = RecommendationRequestContext(
        party_size=4,
        weather=WeatherContext(condition=None, available=False),
        is_weekend=False,
    )
    recommendations = RecommendationEngine().recommend(restaurants, context)

    message = format_recommendations(recommendations, context)

    assert "1. 김치찌개집" in message["text"]
    assert "한식" in message["text"]
    assert "날씨 정보" in message["text"]
