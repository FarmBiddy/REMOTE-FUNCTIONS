"""Composition root: FastAPI app, lifespan, and route mounting."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router

logger = logging.getLogger(__name__)


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

app.include_router(router)
