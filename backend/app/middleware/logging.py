import json
import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(level=getattr(logging, level_name, logging.INFO))
        self.logger = logging.getLogger("lunch-menu-recommender")

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = int((time.perf_counter() - start) * 1000)
        payload = {
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "ms": duration,
        }
        self.logger.info(json.dumps(payload, ensure_ascii=False))
        return response
