from __future__ import annotations

from dataclasses import dataclass

from app.models import PriceRange, RecommendationRequest, Restaurant, ScoredRestaurant


WEATHER_PREFERENCES = {
    "sunny": {"outdoor": 1.0, "cafe": 0.8, "bakery": 0.7, "korean": 0.6, "general": 0.5},
    "cloudy": {"cafe": 1.0, "ramen": 0.8, "korean": 0.7, "chicken": 0.5, "general": 0.4},
    "rainy": {"cafe": 1.0, "japanese": 0.8, "bunsik": 0.7, "korean": 0.6, "general": 0.4},
    "snowy": {"korean": 1.0, "hotpot": 0.8, "cafe": 0.7, "japanese": 0.6, "general": 0.3},
}

MOOD_PREFERENCES = {
    "happy": {"korean": 0.9, "chicken": 0.8, "korean bbq": 1.0, "pizza": 0.8},
    "normal": {"korean": 0.7, "cafe": 0.8, "general": 0.6},
    "sad": {"soup": 0.9, "ramen": 0.8, "cafe": 0.7, "japanese": 0.6},
    "tired": {"korean": 0.8, "japanese": 0.7, "cafe": 0.6},
}

EVENT_PREFERENCES = {
    "team_dinner": {"korean bbq": 1.0, "korean": 0.9, "japanese": 0.8},
    "date": {"cafe": 0.95, "dessert": 0.9, "japanese": 0.85},
    "solo": {"ramen": 0.85, "korean": 0.75, "cafe": 0.65},
    "diet": {"salad": 1.0, "healthy": 0.9, "vegan": 0.85, "korean": 0.7},
    "none": {"general": 0.6},
}


def _category_score(category: str, preference_map: dict[str, float], fallback: float) -> float:
    lowered = (category or "").lower()
    for keyword, score in preference_map.items():
        if keyword in lowered:
            return min(1.0, score)
    return fallback


@dataclass
class RecommendationEngine:
    max_radius: int = 200

    def recommend(
        self,
        restaurants: list[Restaurant],
        criteria: RecommendationRequest,
        exclude_ids: set[str] | None = None,
        top_n: int = 3,
    ) -> list[ScoredRestaurant]:
        excluded = exclude_ids or set()
        candidates = [item for item in restaurants if item.id not in excluded]

        scored: list[ScoredRestaurant] = []
        for candidate in candidates:
            weather_score = _category_score(
                candidate.category,
                WEATHER_PREFERENCES.get(criteria.weather.value, {}),
                0.5,
            )
            mood_score = _category_score(
                candidate.category,
                MOOD_PREFERENCES.get(criteria.mood.value, {}),
                0.5,
            )
            event_score = _category_score(
                candidate.category,
                EVENT_PREFERENCES.get(criteria.event.value, {}),
                0.5,
            )
            context_score = (weather_score + mood_score + event_score) / 3.0

            distance_factor = max(0.0, 1.0 - (candidate.distance / float(self.max_radius)))
            price_penalty = abs(self._price_order(criteria.price_range) - self._price_order(candidate.price_range))
            price_score = max(0.0, 1.0 - 0.5 * price_penalty)

            final_score = (
                0.4 * weather_score
                + 0.3 * context_score
                + 0.2 * distance_factor
                + 0.1 * price_score
            )

            scored.append(
                ScoredRestaurant(
                    id=candidate.id,
                    name=candidate.name,
                    category=candidate.category,
                    address=candidate.address,
                    latitude=candidate.latitude,
                    longitude=candidate.longitude,
                    distance=candidate.distance,
                    price_range=candidate.price_range,
                    naver_map_url=candidate.naver_map_url,
                    score=round(final_score, 4),
                )
            )

        scored.sort(key=lambda item: (item.score, -item.distance), reverse=True)
        return scored[: max(0, top_n)]

    def _price_order(self, price_range: PriceRange) -> int:
        if price_range == PriceRange.low:
            return 0
        if price_range == PriceRange.medium:
            return 1
        return 2
