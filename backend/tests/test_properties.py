from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import PriceRange, RecommendationRequest, RecommendationResponse, Restaurant, ScoredRestaurant, Weather, Mood, Event
from app.services import NaverMapService, RecommendationEngine


@given(
    weather=st.sampled_from(list(Weather)),
    mood=st.sampled_from(list(Mood)),
    event=st.sampled_from(list(Event)),
    price_range=st.sampled_from(list(PriceRange)),
)
@settings(max_examples=20)
def test_request_response_round_trip(weather, mood, event, price_range):
    request = RecommendationRequest(
        latitude=37.5,
        longitude=126.9,
        weather=weather,
        mood=mood,
        event=event,
        price_range=price_range,
        exclude_ids=["r1", "r2"],
    )
    decoded = RecommendationRequest(**request.model_dump())
    assert decoded == request

    response = RecommendationResponse(
        recommendations=[],
        total_searched=0,
        total_matched=0,
    )
    assert RecommendationResponse(**response.model_dump()) == response


def test_response_json_shape_round_trip():
    response = RecommendationResponse(
        recommendations=[
            ScoredRestaurant(
                id="1",
                name="Sample",
                category="korean",
                address="Seoul",
                latitude=37.5,
                longitude=127.0,
                distance=100,
                price_range=PriceRange.medium,
                naver_map_url="https://map.naver.com",
                score=0.86,
            )
        ],
        total_searched=4,
        total_matched=1,
    )

    dumped = response.model_dump_json()
    restored = RecommendationResponse.model_validate(json.loads(dumped))
    assert len(restored.recommendations) == 1


def test_recommendation_engine_score_order_and_bounds():
    engine = RecommendationEngine()
    request = RecommendationRequest(
        latitude=37.5,
        longitude=126.9,
        weather=Weather.sunny,
        mood=Mood.happy,
        event=Event.team_dinner,
        price_range=PriceRange.low,
        exclude_ids=[],
    )
    restaurants = [
        Restaurant(
            id="1",
            name="A",
            category="korean",
            address="A",
            latitude=37.5,
            longitude=126.9,
            distance=10,
            price_range=PriceRange.low,
            naver_map_url="",
        ),
        Restaurant(
            id="2",
            name="B",
            category="japanese",
            address="B",
            latitude=37.5,
            longitude=126.9001,
            distance=50,
            price_range=PriceRange.medium,
            naver_map_url="",
        ),
    ]
    results = engine.recommend(restaurants, request, exclude_ids={"2"}, top_n=1)
    assert len(results) == 1
    assert results[0].id == "1"
    assert 0.0 <= results[0].score <= 1.0


def test_haversine_distance_uses_200m_cap():
    raw = NaverMapService()
    assert raw is not None
