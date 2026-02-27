from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class APIStatusResponse(str, Enum):
    healthy = "healthy"
    degraded = "degraded"


class Weather(str, Enum):
    sunny = "sunny"
    cloudy = "cloudy"
    rainy = "rainy"
    snowy = "snowy"


class Mood(str, Enum):
    happy = "happy"
    normal = "normal"
    sad = "sad"
    tired = "tired"


class Event(str, Enum):
    team_dinner = "team_dinner"
    date = "date"
    solo = "solo"
    diet = "diet"
    none = "none"


class PriceRange(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RecommendationRequest(BaseModel):
    latitude: float
    longitude: float
    weather: Weather
    mood: Mood
    event: Event
    price_range: PriceRange
    exclude_ids: list[str] = Field(default_factory=list)


class Restaurant(BaseModel):
    id: str
    name: str
    category: str
    address: str
    latitude: float
    longitude: float
    distance: int
    price_range: PriceRange
    naver_map_url: str


class ScoredRestaurant(BaseModel):
    id: str
    name: str
    category: str
    address: str
    latitude: float
    longitude: float
    distance: int
    price_range: PriceRange
    naver_map_url: str
    score: float


class RecommendationResponse(BaseModel):
    recommendations: list[ScoredRestaurant]
    total_searched: int
    total_matched: int


class HealthResponse(BaseModel):
    status: str
    version: str


class APIErrorResponse(BaseModel):
    detail: str


class RestaurantItem(BaseModel):
    id: str | None = None
    title: str | None = None
    category: str | None = None
    roadAddress: str | None = None
    x: str | None = None
    y: str | None = None


class APIHealthResponse(BaseModel):
    status: APIStatusResponse = APIStatusResponse.healthy
    version: str = "1.0.0"
