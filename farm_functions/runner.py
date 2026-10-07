"""Run a named function. Missing numbers are requested, never guessed."""

from __future__ import annotations

from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

from farm_functions.errors import (
    MISSING_REQUIRED,
    attach_issues,
    invalid_inputs_envelope,
    issue,
    map_validation_error,
    missing_required_issues,
    non_object_envelope,
    null_not_allowed_issues,
    unknown_calculation_envelope,
    unknown_field_issues,
)
from farm_functions.registry import INPUT_MODELS, get_function
from farm_functions.schemas import missing_field_entry
from farm_functions.version import ENGINE_VERSION


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


def _path(loc: tuple[Any, ...]) -> str:
    """Pydantic loc → caller path, e.g. ``months[3].milk_price``."""
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def _nested_needs_input(
    name: str, payload: dict[str, Any], known: tuple[str, ...], exc: ValidationError
) -> dict[str, Any] | None:
    """ADR-0027: when the only problems are missing nested fields, ask for them."""
    errors = exc.errors()
    if not errors or any(err["type"] != "missing" for err in errors):
        return None
    missing = []
    issues = []
    for err in errors:
        leaf, path = str(err["loc"][-1]), _path(err["loc"])
        missing.append({**missing_field_entry(leaf), "path": path})
        issues.append(issue(MISSING_REQUIRED, f"{path} is required", field=leaf, details={"path": path}))
    return attach_issues(
        {
            "status": "needs_input",
            "function": name,
            "missing": missing,
            "provided": _present_keys(payload, known),
        },
        issues,
    )


def run_function(name: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run one calculation; every envelope carries ``meta.engine_version`` (ADR-0050)."""
    return with_meta(_run(name, inputs))


def with_meta(envelope: dict[str, Any]) -> dict[str, Any]:
    return {**envelope, "meta": {"engine_version": ENGINE_VERSION}}


def _run(name: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
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
        return _nested_needs_input(name, payload, known, exc) or invalid_inputs_envelope(
            name, map_validation_error(exc)
        )

    try:
        result = spec.handler(**parsed.model_dump())
    except ValidationError as exc:
        return invalid_inputs_envelope(name, map_validation_error(exc))

    return {
        "status": "ok",
        "function": name,
        "result": result,
    }
