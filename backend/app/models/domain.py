"""Domain contracts shared by Slack lunch recommendation services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class WeatherCategory(StrEnum):
    """Normalized weather states used by the recommendation layer."""

    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    HOT = "hot"
    COLD = "cold"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float
    label: str | None = None


@dataclass(frozen=True, slots=True)
class RestaurantCandidate:
    provider_id: str
    name: str
    category: str
    distance_meters: int | None
    address: str | None
    road_address: str | None
    latitude: float | None
    longitude: float | None
    map_url: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WeatherContext:
    category: WeatherCategory
    description: str | None = None
    temperature_celsius: float | None = None
    provider_code: int | None = None
    unavailable_reason: str | None = None

    @property
    def is_available(self) -> bool:
        return self.category is not WeatherCategory.UNAVAILABLE
