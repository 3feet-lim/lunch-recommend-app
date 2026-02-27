from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Iterable

import httpx

from app.models import Restaurant, PriceRange


class SearchError(RuntimeError):
    pass


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    # Simple haversine distance helper in meters.
    radius = 6371000.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
    return int(radius * c)


def _infer_price_range(text: str) -> PriceRange:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["one", "1", "저가", "저렴", "한식", "분식"]):
        return PriceRange.low
    if any(keyword in lowered for keyword in ["high", "2~3", "뷔페", "스테이크", "이탈리"]):
        return PriceRange.high
    return PriceRange.medium


@dataclass
class NaverSearchItem:
    item_id: str
    name: str
    category: str
    address: str
    lat: float
    lon: float


class NaverMapService:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = "https://openapi.naver.com/v1/search/local",
        timeout_seconds: float = 5.0,
    ) -> None:
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET", "")
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    async def search_nearby_restaurants(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 200,
    ) -> list[Restaurant]:
        if not self.client_id or not self.client_secret:
            raise SearchError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET are not set")

        limit_radius = min(max(radius_meters, 1), 200)
        query = "식당"

        params = {
            "query": query,
            "display": 100,
            "start": 1,
            "sort": "random",
        }

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise SearchError("Naver API request timed out") from exc
        except httpx.HTTPError as exc:
            raise SearchError("Naver API request failed") from exc

        if response.status_code >= 500:
            raise SearchError(f"Naver API error: {response.status_code}")
        if response.status_code >= 400:
            # Keep this as business error to propagate as Bad Gateway in route layer.
            raise SearchError(f"Naver API request invalid: {response.status_code}")

        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
        restaurants: list[Restaurant] = []

        for raw in self._normalize_items(items):
            distance = haversine_distance_meters(latitude, longitude, raw.lat, raw.lon)
            if distance > limit_radius:
                continue
            restaurant = Restaurant(
                id=raw.item_id,
                name=raw.name,
                category=raw.category,
                address=raw.address,
                latitude=raw.lat,
                longitude=raw.lon,
                distance=distance,
                price_range=_infer_price_range(raw.category),
                naver_map_url=f"https://map.naver.com/p/search/{raw.name}",
            )
            restaurants.append(restaurant)

        restaurants.sort(key=lambda item: item.distance)
        return restaurants

    def _normalize_items(self, items: Iterable[dict]) -> list[NaverSearchItem]:
        normalized: list[NaverSearchItem] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            item_id = str(item.get("id") or item.get("placeId") or item.get("link") or "")
            raw_name = item.get("title") or item.get("name") or "restaurant"
            # Remove HTML strong tags from search API response.
            name = str(raw_name).replace("<b>", "").replace("</b>", "").strip()
            category = str(item.get("category") or item.get("categoryName") or "general").strip()
            address = str(item.get("roadAddress") or item.get("address") or "").strip()
            longitude = self._parse_coordinate(item.get("x"))
            latitude = self._parse_coordinate(item.get("y"))

            if latitude is None or longitude is None:
                continue

            normalized.append(
                NaverSearchItem(
                    item_id=item_id or name,
                    name=name,
                    category=category,
                    address=address,
                    lat=latitude,
                    lon=longitude,
                )
            )
        return normalized

    def _parse_coordinate(self, value: object) -> float | None:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        return number
