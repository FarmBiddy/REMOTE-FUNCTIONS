"""HTTP routes for discovery, probes, demo, and per-function calculation runs."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from farm_functions.errors import invalid_json_envelope, unknown_calculation_envelope
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import CALCULATION_CATALOGUE, describe_function, list_functions
from farm_functions.runner import run_function, with_meta

router = APIRouter()

# Swagger "Try it out" examples: one real payload per ID (Joe Bloggs' farm),
# kept valid by tests/test_examples.py (ADR-0050).
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "sample_data" / "examples"


def load_example(key: str) -> dict[str, Any]:
    path = EXAMPLES_DIR / f"{key}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


_INVALID_JSON = object()


async def _read_payload(request: Request) -> Any:
    """Parse JSON body without FastAPI required-field validation (needs_input stays in runner)."""
    body = await request.body()
    if not body:
        return {}
    try:
        data = await request.json()
    except ValueError:  # JSONDecodeError / bad encoding
        return _INVALID_JSON
    if data is None:
        return {}
    if not isinstance(data, dict):
        return data  # runner returns a clear error for non-objects
    return data


def _register_function_routes() -> None:
    """One concrete POST per catalogue ID so OpenAPI shows real input fields."""
    for spec in CALCULATION_CATALOGUE:
        key = spec.id
        model = spec.input_model
        example = load_example(key)
        schema = model.model_json_schema()

        def make_handler(function_key: str, description: str):
            async def endpoint(request: Request) -> dict[str, Any]:
                payload = await _read_payload(request)
                if payload is _INVALID_JSON:
                    return with_meta(invalid_json_envelope(function_key))
                return run_function(function_key, payload)

            endpoint.__name__ = f"run_{function_key.replace('.', '_')}"
            endpoint.__doc__ = description
            return endpoint

        router.add_api_route(
            path=f"/v1/functions/{key}/run",
            endpoint=make_handler(key, spec.description),
            methods=["POST"],
            name=f"run_{key.replace('.', '_')}",
            summary=spec.description,
            openapi_extra={
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": schema,
                            "example": example,
                        }
                    },
                }
            },
        )


@router.get("/livez")
def livez() -> dict[str, bool]:
    return {"ok": True}


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


_READY = {"ready": False}


def set_ready(value: bool) -> None:
    """Flipped by the app lifespan: ready only after startup, not during shutdown."""
    _READY["ready"] = value


@router.get("/readyz")
def readyz() -> JSONResponse:
    """Readiness for deploy health checks: 200 once started, 503 otherwise."""
    return JSONResponse(status_code=200 if _READY["ready"] else 503, content=_READY)


@router.get("/v1/functions")
def functions() -> dict[str, Any]:
    return {"functions": list_functions()}


@router.get("/v1/functions/{key}")
def function_detail(key: str) -> Any:
    """Input schema and units for one calculation ID (ADR-0048)."""
    detail = describe_function(key)
    if detail is None:
        return JSONResponse(status_code=404, content=unknown_calculation_envelope(key))
    return detail


@router.post("/v1/demo/pl-summary")
def demo_pl_summary() -> dict[str, Any]:
    return run_function("pl.summary", load_sample_inputs())


_register_function_routes()


@router.api_route(
    "/v1/functions/{name}/run",
    methods=["POST"],
    include_in_schema=False,
)
async def run_unknown_function(name: str, request: Request) -> JSONResponse:
    """Catch-all for unknown calculation IDs. Catalogue routes are registered first."""
    await _read_payload(request)
    return JSONResponse(status_code=404, content=unknown_calculation_envelope(name))
