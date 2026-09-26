"""Composition root: FastAPI app, lifespan, CORS, and route mounting."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

logger = logging.getLogger(__name__)

_DEFAULT_CORS_ORIGINS = ("http://localhost:3000",)


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_CORS_ORIGINS)
    return [part.strip() for part in raw.split(",") if part.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("API ready")
    yield


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
    allow_headers=["Content-Type"],
)

app.include_router(router)
