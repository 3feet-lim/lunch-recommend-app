"""OpenWeather current-weather client with graceful unavailable fallback."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

from app.models.domain import Coordinates, WeatherCategory, WeatherContext
from app.services.external_api_errors import MissingCredentialError, UpstreamServiceError


class OpenWeatherClient:
    DEFAULT_BASE_URL = "https://api.openweathermap.org"
    CURRENT_WEATHER_PATH = "/data/2.5/weather"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        base_url: str = DEFAULT_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENWEATHER_API_KEY")
        self.timeout_seconds = timeout_seconds or float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "3"))
        self.base_url = base_url.rstrip("/")
        self._client = http_client

    async def fetch_current_weather(self, coordinates: Coordinates) -> WeatherContext:
        if not self.api_key:
            raise MissingCredentialError("OpenWeather API key is not configured")
        try:
            response = await self._get(
                self.CURRENT_WEATHER_PATH,
                params={
                    "lat": str(coordinates.latitude),
                    "lon": str(coordinates.longitude),
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "kr",
                },
            )
        except httpx.TimeoutException:
            return WeatherContext(
                category=WeatherCategory.UNAVAILABLE,
                unavailable_reason="timeout",
            )
        except httpx.HTTPError:
            return WeatherContext(
                category=WeatherCategory.UNAVAILABLE,
                unavailable_reason="transport_error",
            )

        if response.status_code >= 400:
            return WeatherContext(
                category=WeatherCategory.UNAVAILABLE,
                unavailable_reason="provider_error",
            )
        payload = _json_or_error(response)
        return _weather_from_payload(payload)

    async def _get(self, path: str, *, params: Mapping[str, Any]) -> httpx.Response:
        url = f"{self.base_url}{path}"
        if self._client is not None:
            return await self._client.get(url, params=params, timeout=self.timeout_seconds)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await client.get(url, params=params)


def _weather_from_payload(payload: dict[str, Any]) -> WeatherContext:
    weather_items = payload.get("weather")
    first_weather = weather_items[0] if isinstance(weather_items, list) and weather_items else {}
    main = str(first_weather.get("main", "")).lower() if isinstance(first_weather, dict) else ""
    description = first_weather.get("description") if isinstance(first_weather, dict) else None
    provider_code = first_weather.get("id") if isinstance(first_weather, dict) else None
    main_payload = payload.get("main")
    temperature = _optional_float(
        main_payload.get("temp") if isinstance(main_payload, dict) else None
    )

    category = WeatherCategory.CLOUDY
    if main in {"thunderstorm", "drizzle", "rain"}:
        category = WeatherCategory.RAIN
    elif main == "snow":
        category = WeatherCategory.SNOW
    elif temperature is not None and temperature >= 28.0:
        category = WeatherCategory.HOT
    elif temperature is not None and temperature <= 5.0:
        category = WeatherCategory.COLD
    elif main == "clear":
        category = WeatherCategory.CLEAR
    elif main in {
        "clouds",
        "mist",
        "smoke",
        "haze",
        "dust",
        "fog",
        "sand",
        "ash",
        "squall",
        "tornado",
    }:
        category = WeatherCategory.CLOUDY

    return WeatherContext(
        category=category,
        description=str(description) if description else None,
        temperature_celsius=temperature,
        provider_code=_optional_int(provider_code),
    )


def _json_or_error(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamServiceError("provider response was not JSON") from exc
    if not isinstance(payload, dict):
        raise UpstreamServiceError("provider response JSON was not an object")
    return payload


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
