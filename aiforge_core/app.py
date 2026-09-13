"""FastAPI app factory: /health, JSON request logs, per-IP rate limit, static UI."""

import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("aiforge")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "ts": round(record.created, 3),
        }
        if hasattr(record, "extra_fields"):
            payload.update(record.extra_fields)
        return json.dumps(payload)


def _setup_json_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


class RateLimiter:
    """Sliding-window limit per client IP. Protects free LLM quotas on demos."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        window = self.hits[ip]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= self.per_minute:
            return False
        window.append(now)
        return True


def create_app(
    title: str = "aiforge app",
    static_dir: str | Path | None = None,
    rate_limit_per_min: int | None = None,
    exempt_paths: tuple[str, ...] = ("/health",),
) -> FastAPI:
    _setup_json_logging()
    app = FastAPI(title=title)
    limit = rate_limit_per_min if rate_limit_per_min is not None else int(
        os.getenv("APP_RATE_LIMIT_PER_MIN", "30")
    )
    limiter = RateLimiter(limit)
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def rate_limit_and_log(request: Request, call_next):
        path = request.url.path
        if path not in exempt_paths and not path.startswith("/static"):
            ip = request.client.host if request.client else "unknown"
            if not limiter.allow(ip):
                return JSONResponse(
                    {"detail": "Rate limit reached, please wait a minute."}, status_code=429
                )
        start = time.monotonic()
        response = await call_next(request)
        logger.info(
            "request",
            extra={
                "extra_fields": {
                    "path": path,
                    "method": request.method,
                    "status": response.status_code,
                    "ms": int((time.monotonic() - start) * 1000),
                }
            },
        )
        return response

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    if static_dir is not None and Path(static_dir).is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
