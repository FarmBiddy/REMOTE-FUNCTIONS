"""Run a named function. Missing numbers are requested, never guessed."""

from typing import Any

from pydantic import ValidationError

from farm_functions.registry import get_function
from farm_functions.schemas import INPUT_MODELS, missing_field_entry


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
    null_keys = [key for key in known if key in payload and payload[key] is None]
    if null_keys:
        return {
            "status": "error",
            "function": name,
            "message": "One or more values are invalid.",
            "details": [
                {"field": key, "reason": "null is not a valid value"}
                for key in null_keys
            ],
        }

    missing_keys = [key for key in spec.required if key not in payload]
    if missing_keys:
        return {
            "status": "needs_input",
            "function": name,
            "missing": [missing_field_entry(key) for key in missing_keys],
            "provided": _present_keys(payload, known),
        }

    model = INPUT_MODELS[name]
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        return {
            "status": "error",
            "function": name,
            "message": "One or more values are invalid.",
            "details": exc.errors(),
        }

    result = spec.handler(**parsed.model_dump())
    return {
        "status": "ok",
        "function": name,
        "result": result,
    }
