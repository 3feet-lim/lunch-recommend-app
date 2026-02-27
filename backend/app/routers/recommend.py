from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import (
    APIErrorResponse,
    RecommendationRequest,
    RecommendationResponse,
    Restaurant,
)
from app.services import NaverMapService, SearchError, RecommendationEngine

recommend_router = APIRouter()

naver_service = NaverMapService()
recommendation_engine = RecommendationEngine()


@recommend_router.post("/recommend", response_model=RecommendationResponse, responses={
    422: {"model": APIErrorResponse},
    500: {"model": APIErrorResponse},
    502: {"model": APIErrorResponse},
    504: {"model": APIErrorResponse},
})
async def recommend(request: RecommendationRequest) -> RecommendationResponse:
    try:
        restaurants = await naver_service.search_nearby_restaurants(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_meters=200,
        )
    except SearchError as exc:
        message = str(exc)
        status_code = 502
        if "timed out" in message.lower():
            status_code = 504
        raise HTTPException(status_code=status_code, detail=message)

    recommendations = recommendation_engine.recommend(
        restaurants=restaurants,
        criteria=request,
        exclude_ids=set(request.exclude_ids),
        top_n=3,
    )
    return RecommendationResponse(
        recommendations=[r for r in recommendations],
        total_searched=len(restaurants),
        total_matched=len(recommendations),
    )
