"""Minimal FastAPI app so a client can discover and run functions."""

from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import FUNCTIONS, list_functions
from farm_functions.runner import run_function
from farm_functions.schemas import INPUT_MODELS


app = FastAPI(
    title="Farm cost and revenue functions",
    version="0.1.0",
    description="Pure P&L calculations with an explicit missing-input contract.",
)


# Sample-farm-style defaults for Swagger Try it out examples.
_EXAMPLE_VALUES: dict[str, float] = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
    "biss": 20000,
    "acres": 5000,
    "other_grants": 0,
    "cattle_sales": 15000,
    "lamb_sales": 0,
    "wool": 0,
    "other": 0,
    "feed": 80000,
    "fertiliser": 15000,
    "vet": 5000,
    "contractor": 10000,
    "labour": 40000,
    "insurance": 4000,
    "loan_repayments": 12000,
    "fuel": 6000,
    "electricity": 3000,
    "revenue": 240000,
    "costs": 175000,
}


def _example_for_model(model: type[BaseModel]) -> dict[str, float]:
    return {
        name: _EXAMPLE_VALUES[name]
        for name in model.model_fields
        if name in _EXAMPLE_VALUES
    }


async def _read_payload(request: Request) -> dict[str, Any]:
    """Parse JSON body without FastAPI required-field validation (needs_input stays in runner)."""
    body = await request.body()
    if not body:
        return {}
    data = await request.json()
    if data is None:
        return {}
    if not isinstance(data, dict):
        return data  # runner returns a clear error for non-objects
    return data


def _register_function_routes() -> None:
    """One concrete POST per function so OpenAPI shows real input fields."""
    for key, model in INPUT_MODELS.items():
        spec = FUNCTIONS[key]
        example = _example_for_model(model)
        schema = model.model_json_schema()

        def make_handler(function_key: str, description: str):
            async def endpoint(request: Request) -> dict[str, Any]:
                payload = await _read_payload(request)
                return run_function(function_key, payload)

            endpoint.__name__ = f"run_{function_key.replace('.', '_')}"
            endpoint.__doc__ = description
            return endpoint

        app.add_api_route(
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


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/v1/functions")
def functions() -> dict[str, Any]:
    return {"functions": list_functions()}


@app.post("/v1/demo/pl-summary")
def demo_pl_summary() -> dict[str, Any]:
    return run_function("pl.summary", load_sample_inputs())


_register_function_routes()
