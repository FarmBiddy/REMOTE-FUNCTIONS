"""Composition root: FastAPI app, lifespan, CORS, and route mounting."""

import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router, set_ready
from farm_functions.errors import UNAUTHORIZED

logger = logging.getLogger(__name__)

_DEFAULT_CORS_ORIGINS = ("http://localhost:3000",)


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_CORS_ORIGINS)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _service_key() -> str:
    """Service-to-service key (ADR-0049). Empty = open (local development only)."""
    return os.environ.get("ENGINE_API_KEY", "").strip()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not _service_key():
        logger.warning("ENGINE_API_KEY not set: /v1 routes are open (local development only)")
    set_ready(True)
    logger.info("API ready")
    yield
    set_ready(False)


app = FastAPI(
    title="Farm cost and revenue functions",
    version="0.1.0",
    description="Pure P&L calculations with an explicit missing-input contract.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.middleware("http")
async def require_service_key(request: Request, call_next):
    """Calls to /v1 must carry ``Authorization: Bearer <ENGINE_API_KEY>`` when a key is set.

    Probes (/livez, /health, /readyz) and docs stay open. The key identifies the
    calling service (the App Platform), never an end user (ADR-0002, ADR-0049).
    """
    key = _service_key()
    if key and request.url.path.startswith("/v1/") and request.method != "OPTIONS":
        sent = request.headers.get("authorization", "")
        token = sent[7:] if sent.lower().startswith("bearer ") else ""
        if not hmac.compare_digest(token.encode(), key.encode()):
            message = "Missing or invalid service token."
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "message": message,
                    "error": {"code": UNAUTHORIZED, "message": message},
                    "errors": [{"code": UNAUTHORIZED, "message": message}],
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


app.include_router(router)
