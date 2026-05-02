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


@dataclass(frozen=True, slots=True, init=False)
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

    def __init__(
        self,
        provider_id: str | None = None,
        name: str = "",
        category: str = "음식점",
        distance_meters: int | None = None,
        address: str | None = None,
        road_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        map_url: str | None = None,
        raw: dict[str, Any] | None = None,
        *,
        id: str | None = None,
        place_url: str | None = None,
    ) -> None:
        object.__setattr__(self, "provider_id", provider_id or id or "")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "distance_meters", distance_meters)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "road_address", road_address)
        object.__setattr__(self, "latitude", latitude)
        object.__setattr__(self, "longitude", longitude)
        object.__setattr__(self, "map_url", map_url or place_url)
        object.__setattr__(self, "raw", raw or {})

    @property
    def id(self) -> str:
        return self.provider_id

    @property
    def place_url(self) -> str | None:
        return self.map_url


@dataclass(frozen=True, slots=True, init=False)
class WeatherContext:
    category: WeatherCategory
    description: str | None = None
    temperature_celsius: float | None = None
    provider_code: int | None = None
    unavailable_reason: str | None = None

    def __init__(
        self,
        category: WeatherCategory | str | None = None,
        description: str | None = None,
        temperature_celsius: float | None = None,
        provider_code: int | None = None,
        unavailable_reason: str | None = None,
        *,
        condition: str | None = None,
        available: bool | None = None,
    ) -> None:
        resolved_category = _coerce_weather_category(category or condition)
        if available is False:
            resolved_category = WeatherCategory.UNAVAILABLE
            unavailable_reason = unavailable_reason or "unavailable"
        object.__setattr__(self, "category", resolved_category)
        object.__setattr__(self, "description", description or condition)
        object.__setattr__(self, "temperature_celsius", temperature_celsius)
        object.__setattr__(self, "provider_code", provider_code)
        object.__setattr__(self, "unavailable_reason", unavailable_reason)

    @property
    def is_available(self) -> bool:
        return self.category is not WeatherCategory.UNAVAILABLE

    @property
    def available(self) -> bool:
        return self.is_available

    @property
    def condition(self) -> str | None:
        return None if self.category is WeatherCategory.UNAVAILABLE else self.category.value


def _coerce_weather_category(value: WeatherCategory | str | None) -> WeatherCategory:
    if isinstance(value, WeatherCategory):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        aliases = {
            "rainy": WeatherCategory.RAIN,
            "rain": WeatherCategory.RAIN,
            "snowy": WeatherCategory.SNOW,
            "snow": WeatherCategory.SNOW,
            "clear": WeatherCategory.CLEAR,
            "sunny": WeatherCategory.CLEAR,
            "clouds": WeatherCategory.CLOUDY,
            "cloudy": WeatherCategory.CLOUDY,
            "hot": WeatherCategory.HOT,
            "cold": WeatherCategory.COLD,
            "unavailable": WeatherCategory.UNAVAILABLE,
        }
        return aliases.get(lowered, WeatherCategory.CLOUDY)
    return WeatherCategory.UNAVAILABLE
