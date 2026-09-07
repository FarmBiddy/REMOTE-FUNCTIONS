"""Minimal FastAPI app so a client can discover and run functions."""

from typing import Any

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import get_function, list_functions
from farm_functions.runner import run_function


# #region agent log
def _dbg(message: str, data: dict, hypothesis_id: str, location: str) -> None:
    import json
    import time
    from pathlib import Path

    payload = {
        "sessionId": "bd25d5",
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
    }
    Path("debug-bd25d5.log").open("a", encoding="utf-8").write(json.dumps(payload) + "\n")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _dbg("api_started", {"title": _app.title}, "A", "api/app.py:lifespan")
    yield


# #endregion

app = FastAPI(
    title="Farm cost and revenue functions",
    version="0.1.0",
    description="Pure P&L calculations with an explicit missing-input contract.",
    lifespan=_lifespan,
)


@app.get("/health")
def health() -> dict[str, bool]:
    # #region agent log
    _dbg("health_hit", {"ok": True}, "A", "api/app.py:health")
    # #endregion
    return {"ok": True}


@app.get("/v1/functions")
def functions() -> dict[str, Any]:
    return {"functions": list_functions()}


@app.post("/v1/functions/{name}/run")
def run(name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if get_function(name) is None:
        raise HTTPException(status_code=404, detail=f"Unknown function: {name}")
    return run_function(name, payload or {})


@app.post("/v1/demo/pl-summary")
def demo_pl_summary() -> dict[str, Any]:
    return run_function("pl.summary", load_sample_inputs())
