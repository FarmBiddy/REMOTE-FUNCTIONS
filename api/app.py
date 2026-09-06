"""Minimal FastAPI app so a client can discover and run functions."""

from typing import Any

from fastapi import FastAPI, HTTPException

from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import get_function, list_functions
from farm_functions.runner import run_function

app = FastAPI(
    title="Farm cost and revenue functions",
    version="0.1.0",
    description="Pure P&L calculations with an explicit missing-input contract.",
)


@app.get("/health")
def health() -> dict[str, bool]:
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
