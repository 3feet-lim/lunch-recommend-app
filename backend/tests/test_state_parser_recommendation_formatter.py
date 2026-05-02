from __future__ import annotations

from pathlib import Path

from app.models.domain import RestaurantCandidate, WeatherCategory, WeatherContext
from app.services.conversation_state import ConversationStateStore, build_conversation_key
from app.services.message_formatter import MessageFormatter
from app.services.parser import next_missing_question, parse_slash_command_text
from app.services.recommendation_engine import RecommendationEngine


def test_parser_extracts_korean_region_party_size_and_context() -> None:
    parsed = parse_slash_command_text("강남역 4명 팀점심")

    assert parsed.region == "강남역"
    assert parsed.party_size == 4
    assert parsed.companion_context == "팀점심"
    assert next_missing_question(parsed) is None


def test_parser_identifies_missing_fields() -> None:
    assert next_missing_question(parse_slash_command_text("")) == "region"
    assert next_missing_question(parse_slash_command_text("강남역")) == "party_size"


def test_conversation_state_uses_prd_key_ttl_and_fingerprint(tmp_path: Path) -> None:
    store = ConversationStateStore(tmp_path / "state.sqlite3", ttl_minutes=30)
    key = build_conversation_key("T1", "C1", "U1")

    state = store.upsert(
        key=key,
        pending_question="party_size",
        region="강남역",
        response_url="https://hooks.slack.test/fake",
        last_request_fingerprint="fp1",
    )

    assert state.key == "T1/C1/U1"
    assert state.pending_question == "party_size"
    assert state.region == "강남역"
    assert store.is_duplicate(key, "fp1")
    assert not store.is_duplicate(key, "fp2")

    reopened = ConversationStateStore(tmp_path / "state.sqlite3", ttl_minutes=30)
    assert reopened.get(key) == state


def test_recommendation_engine_returns_real_candidates_with_reasons() -> None:
    restaurants = [
        RestaurantCandidate(
            provider_id="1",
            name="따뜻한한식",
            category="음식점 > 한식",
            distance_meters=20,
            address="서울 강남구",
            road_address=None,
            latitude=37.5,
            longitude=127.0,
            map_url="https://place.map.kakao.com/1",
            raw={},
        ),
        RestaurantCandidate(
            provider_id="2",
            name="먼카페",
            category="음식점 > 카페",
            distance_meters=120,
            address="서울 강남구",
            road_address=None,
            latitude=37.5,
            longitude=127.0,
            map_url="https://place.map.kakao.com/2",
            raw={},
        ),
    ]

    results = RecommendationEngine().recommend(
        restaurants,
        weather=WeatherContext(category=WeatherCategory.RAIN, description="비"),
        weekday="weekday",
        party_size=4,
        context="팀점심",
    )

    assert [item.name for item in results] == ["따뜻한한식", "먼카페"]
    assert len(results) == 2
    assert "팀" in results[0].reason or "날씨" in results[0].reason or "4명" in results[0].reason


def test_message_formatter_outputs_strict_radius_and_sanitized_errors() -> None:
    formatter = MessageFormatter()

    no_results = formatter.format_no_results(region="강남역", strict_radius_meters=150)["text"]
    assert "150m" in no_results
    assert "넓히지" in no_results

    error = formatter.format_error(
        "Traceback failed https://hooks.slack.com/services/T/B/SECRET xoxb-secret"
    )["text"]
    assert "hooks.slack.com/services" not in error
    assert "xoxb-" not in error
    assert "Traceback" not in error
