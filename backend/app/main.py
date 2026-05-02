from fastapi import FastAPI

from app.routers import health, slack


def create_app() -> FastAPI:
    slack._SEEN_REQUESTS.clear()
    app = FastAPI(title="Slack Lunch Recommendation Bot", version="0.1.0")
    app.include_router(health.router)
    app.include_router(slack.router)
    return app


app = create_app()
