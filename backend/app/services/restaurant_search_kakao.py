"""Kakao Local restaurant search client for strict-radius Slack lunch search."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

from app.models.domain import Coordinates, RestaurantCandidate
from app.services.external_api_errors import MissingCredentialError, UpstreamServiceError, UpstreamTimeoutError


class KakaoLocalClient:
    DEFAULT_BASE_URL = "https://dapi.kakao.com"
    CATEGORY_SEARCH_PATH = "/v2/local/search/category.json"
    RESTAURANT_CATEGORY_GROUP = "FD6"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        radius_meters: int | None = None,
        timeout_seconds: float | None = None,
        base_url: str = DEFAULT_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("KAKAO_REST_API_KEY")
        self.radius_meters = radius_meters or int(os.getenv("RESTAURANT_SEARCH_RADIUS_METERS", "150"))
        self.timeout_seconds = timeout_seconds or float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "3"))
        self.base_url = base_url.rstrip("/")
        self._client = http_client

    async def search_restaurants(
        self,
        coordinates: Coordinates,
        *,
        size: int = 15,
    ) -> list[RestaurantCandidate]:
        if not self.api_key:
            raise MissingCredentialError("Kakao REST API key is not configured")
        bounded_size = max(1, min(size, 15))
        response = await self._get(
            self.CATEGORY_SEARCH_PATH,
            params={
                "category_group_code": self.RESTAURANT_CATEGORY_GROUP,
                "x": str(coordinates.longitude),
                "y": str(coordinates.latitude),
                "radius": str(self.radius_meters),
                "sort": "distance",
                "size": str(bounded_size),
            },
            headers={"Authorization": f"KakaoAK {self.api_key}"},
        )
        if response.status_code >= 400:
            raise UpstreamServiceError("Kakao Local restaurant search failed")
        payload = _json_or_error(response)
        documents = payload.get("documents", [])
        if not isinstance(documents, list):
            raise UpstreamServiceError("Kakao Local response documents were malformed")
        return [_candidate_from_document(document) for document in documents if isinstance(document, dict)]

    async def _get(
        self,
        path: str,
        *,
        params: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                return await self._client.get(url, params=params, headers=headers, timeout=self.timeout_seconds)
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                return await client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError("Kakao Local restaurant search timed out") from exc
        except httpx.HTTPError as exc:
            raise UpstreamServiceError("Kakao Local transport failed") from exc


def _candidate_from_document(document: dict[str, Any]) -> RestaurantCandidate:
    try:
        provider_id = str(document["id"])
        name = str(document["place_name"]).strip()
    except KeyError as exc:
        raise UpstreamServiceError("Kakao Local restaurant document is missing required fields") from exc
    if not provider_id or not name:
        raise UpstreamServiceError("Kakao Local restaurant document has empty required fields")

    return RestaurantCandidate(
        provider_id=provider_id,
        name=name,
        category=str(document.get("category_name") or "음식점"),
        distance_meters=_optional_int(document.get("distance")),
        address=document.get("address_name") or None,
        road_address=document.get("road_address_name") or None,
        latitude=_optional_float(document.get("y")),
        longitude=_optional_float(document.get("x")),
        map_url=document.get("place_url") or None,
        raw=document,
    )


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_or_error(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamServiceError("provider response was not JSON") from exc
    if not isinstance(payload, dict):
        raise UpstreamServiceError("provider response JSON was not an object")
    return payload
