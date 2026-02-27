from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware import RequestLoggingMiddleware
from app.routers.health import health_router
from app.routers.recommend import recommend_router

app = FastAPI(title="lunch-menu-recommender", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(recommend_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "service": "lunch-menu-recommender"}
