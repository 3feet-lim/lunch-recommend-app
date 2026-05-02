from __future__ import annotations

import httpx
import pytest

from app.models.domain import Coordinates, WeatherCategory
from app.services.external_api_errors import MissingCredentialError, RegionNotFoundError, UpstreamServiceError
from app.services.geocoding_naver import NaverGeocodingClient
from app.services.restaurant_search_kakao import KakaoLocalClient
from app.services.weather_openweather import OpenWeatherClient


@pytest.mark.asyncio
async def test_naver_geocoding_uses_query_and_credential_headers() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["client_id"] = request.headers.get("X-NCP-APIGW-API-KEY-ID")
        seen["client_secret"] = request.headers.get("X-NCP-APIGW-API-KEY")
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "addresses": [{"x": "127.0276", "y": "37.4979", "roadAddress": "강남역"}],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = NaverGeocodingClient(
            client_id="cid",
            client_secret="secret",
            http_client=http_client,
        )
        coordinates = await client.geocode_region("강남역")

    assert coordinates == Coordinates(latitude=37.4979, longitude=127.0276, label="강남역")
    assert "query=%EA%B0%95%EB%82%A8%EC%97%AD" in str(seen["url"])
    assert seen["client_id"] == "cid"
    assert seen["client_secret"] == "secret"


@pytest.mark.asyncio
async def test_naver_geocoding_no_result_maps_to_region_not_found() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "OK", "addresses": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = NaverGeocodingClient(client_id="cid", client_secret="secret", http_client=http_client)
        with pytest.raises(RegionNotFoundError):
            await client.geocode_region("없는장소")


@pytest.mark.asyncio
async def test_kakao_restaurant_search_uses_strict_radius_and_fd6_category() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["params"] = dict(request.url.params)
        seen["authorization"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "id": "1",
                        "place_name": "맛집",
                        "category_name": "음식점 > 한식",
                        "distance": "42",
                        "address_name": "서울 강남구",
                        "road_address_name": "서울 강남구 테헤란로",
                        "x": "127.0",
                        "y": "37.5",
                        "place_url": "https://place.map.kakao.com/1",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = KakaoLocalClient(api_key="kakao-key", http_client=http_client)
        restaurants = await client.search_restaurants(Coordinates(latitude=37.5, longitude=127.0), size=99)

    assert seen["authorization"] == "KakaoAK kakao-key"
    assert seen["params"] == {
        "category_group_code": "FD6",
        "x": "127.0",
        "y": "37.5",
        "radius": "150",
        "sort": "distance",
        "size": "15",
    }
    assert len(restaurants) == 1
    assert restaurants[0].provider_id == "1"
    assert restaurants[0].distance_meters == 42


@pytest.mark.asyncio
async def test_kakao_restaurant_search_missing_key_fails_closed() -> None:
    client = KakaoLocalClient(api_key="")
    with pytest.raises(MissingCredentialError):
        await client.search_restaurants(Coordinates(latitude=37.5, longitude=127.0))


@pytest.mark.asyncio
async def test_openweather_normalizes_rain_and_hides_timeout_as_unavailable() -> None:
    async def rain_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["appid"] == "weather-key"
        assert request.url.params["units"] == "metric"
        return httpx.Response(
            200,
            json={"weather": [{"id": 501, "main": "Rain", "description": "비"}], "main": {"temp": 18.5}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(rain_handler)) as http_client:
        client = OpenWeatherClient(api_key="weather-key", http_client=http_client)
        weather = await client.fetch_current_weather(Coordinates(latitude=37.5, longitude=127.0))

    assert weather.category is WeatherCategory.RAIN
    assert weather.description == "비"
    assert weather.temperature_celsius == 18.5

    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as http_client:
        client = OpenWeatherClient(api_key="weather-key", http_client=http_client)
        weather = await client.fetch_current_weather(Coordinates(latitude=37.5, longitude=127.0))

    assert weather.category is WeatherCategory.UNAVAILABLE
    assert weather.unavailable_reason == "timeout"


@pytest.mark.asyncio
async def test_openweather_malformed_json_raises_safe_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenWeatherClient(api_key="weather-key", http_client=http_client)
        with pytest.raises(UpstreamServiceError):
            await client.fetch_current_weather(Coordinates(latitude=37.5, longitude=127.0))
