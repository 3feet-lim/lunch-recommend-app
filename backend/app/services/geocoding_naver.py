"""Naver Maps Geocoding API client.

Uses NAVER Cloud's REST geocoding endpoint and credential headers documented for
Naver Maps Geocoding. The client is intentionally narrow: it resolves a human
region/address string to the first coordinate candidate and maps provider
failures into safe domain errors.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

from app.models.domain import Coordinates
from app.services.external_api_errors import (
    MissingCredentialError,
    RegionNotFoundError,
    UpstreamServiceError,
    UpstreamTimeoutError,
)


class NaverGeocodingClient:
    DEFAULT_BASE_URL = "https://naveropenapi.apigw.ntruss.com"
    GEOCODE_PATH = "/map-geocode/v2/geocode"

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout_seconds: float | None = None,
        base_url: str = DEFAULT_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id if client_id is not None else (os.getenv("NAVER_GEOCODING_CLIENT_ID") or os.getenv("NAVER_CLIENT_ID"))
        self.client_secret = (
            client_secret
            if client_secret is not None
            else (os.getenv("NAVER_GEOCODING_CLIENT_SECRET") or os.getenv("NAVER_CLIENT_SECRET"))
        )
        self.timeout_seconds = timeout_seconds or float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "3"))
        self.base_url = base_url.rstrip("/")
        self._client = http_client

    async def geocode_region(self, query: str) -> Coordinates:
        normalized_query = query.strip()
        if not normalized_query:
            raise RegionNotFoundError("region query is empty")
        if not self.client_id or not self.client_secret:
            raise MissingCredentialError("Naver geocoding credentials are not configured")

        response = await self._get(
            self.GEOCODE_PATH,
            params={"query": normalized_query},
            headers={
                "X-NCP-APIGW-API-KEY-ID": self.client_id,
                "X-NCP-APIGW-API-KEY": self.client_secret,
            },
        )
        payload = _json_or_error(response)
        status = str(payload.get("status", ""))
        if response.status_code >= 400 or status.upper() == "ERROR":
            raise UpstreamServiceError("Naver geocoding request failed")

        addresses = payload.get("addresses")
        if not isinstance(addresses, list) or not addresses:
            raise RegionNotFoundError(f"region not found: {normalized_query}")

        first = addresses[0]
        try:
            longitude = float(first["x"])
            latitude = float(first["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UpstreamServiceError("Naver geocoding response is malformed") from exc

        label = first.get("roadAddress") or first.get("jibunAddress") or normalized_query
        return Coordinates(latitude=latitude, longitude=longitude, label=label)

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
            raise UpstreamTimeoutError("Naver geocoding timed out") from exc
        except httpx.HTTPError as exc:
            raise UpstreamServiceError("Naver geocoding transport failed") from exc


def _json_or_error(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamServiceError("provider response was not JSON") from exc
    if not isinstance(payload, dict):
        raise UpstreamServiceError("provider response JSON was not an object")
    return payload
