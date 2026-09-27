"""Run a named function. Missing numbers are requested, never guessed."""

from __future__ import annotations

from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

from farm_functions.errors import (
    attach_issues,
    invalid_inputs_envelope,
    map_validation_error,
    missing_required_issues,
    non_object_envelope,
    null_not_allowed_issues,
    unknown_calculation_envelope,
    unknown_field_issues,
)
from farm_functions.registry import INPUT_MODELS, get_function
from farm_functions.schemas import missing_field_entry


def _present_keys(inputs: dict[str, Any], spec_keys: tuple[str, ...]) -> list[str]:
    return sorted(
        key
        for key in spec_keys
        if key in inputs and inputs[key] is not None
    )


def _unknown_keys(inputs: dict[str, Any], known: tuple[str, ...]) -> list[str]:
    known_set = set(known)
    return sorted(key for key in inputs if key not in known_set)


def _field_allows_none(model: type[BaseModel], field_name: str) -> bool:
    """True when the field annotation accepts ``None`` (e.g. optional ``ytd``)."""
    field = model.model_fields.get(field_name)
    if field is None:
        return False
    annotation = field.annotation
    if annotation is type(None):
        return True
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        return type(None) in get_args(annotation)
    return False


def run_function(name: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = get_function(name)
    if spec is None:
        return unknown_calculation_envelope(name)

    payload = inputs or {}
    if not isinstance(payload, dict):
        return non_object_envelope(name)

    known = spec.required + spec.optional
    unknown_keys = _unknown_keys(payload, known)
    if unknown_keys:
        return invalid_inputs_envelope(name, unknown_field_issues(unknown_keys))

    model = INPUT_MODELS[name]
    null_keys = sorted(
        key
        for key in known
        if key in payload
        and payload[key] is None
        and not _field_allows_none(model, key)
    )
    if null_keys:
        return invalid_inputs_envelope(name, null_not_allowed_issues(null_keys))

    missing_keys = [key for key in spec.required if key not in payload]
    if missing_keys:
        return attach_issues(
            {
                "status": "needs_input",
                "function": name,
                "missing": [missing_field_entry(key) for key in missing_keys],
                "provided": _present_keys(payload, known),
            },
            missing_required_issues(missing_keys),
        )

    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        return invalid_inputs_envelope(name, map_validation_error(exc))

    try:
        result = spec.handler(**parsed.model_dump())
    except ValidationError as exc:
        return invalid_inputs_envelope(name, map_validation_error(exc))

    return {
        "status": "ok",
        "function": name,
        "result": result,
    }
