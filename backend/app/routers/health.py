from fastapi import APIRouter

from app.models import HealthResponse

health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", version="1.0.0")
