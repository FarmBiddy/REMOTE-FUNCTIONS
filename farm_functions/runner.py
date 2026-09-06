"""Run a named function. Missing numbers are requested, never guessed."""

from typing import Any

from pydantic import ValidationError

from farm_functions.registry import get_function
from farm_functions.schemas import INPUT_MODELS


def _present_keys(inputs: dict[str, Any], spec_keys: tuple[str, ...]) -> list[str]:
    return sorted(
        key
        for key in spec_keys
        if key in inputs and inputs[key] is not None
    )


def run_function(name: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = get_function(name)
    if spec is None:
        return {"status": "error", "message": f"Unknown function: {name}"}

    payload = inputs or {}
    if not isinstance(payload, dict):
        return {
            "status": "error",
            "function": name,
            "message": "Inputs must be a JSON object of field names to numbers.",
        }

    known = spec.required + spec.optional
    missing = [key for key in spec.required if payload.get(key) is None]
    if missing:
        return {
            "status": "needs_input",
            "function": name,
            "missing": missing,
            "provided": _present_keys(payload, known),
        }

    model = INPUT_MODELS[name]
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        return {
            "status": "error",
            "function": name,
            "message": "One or more values are not valid numbers.",
            "details": exc.errors(),
        }

    result = spec.handler(**parsed.model_dump())
    return {
        "status": "ok",
        "function": name,
        "result": result,
    }
