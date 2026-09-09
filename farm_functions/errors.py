"""Stable machine-readable calculation error codes for the runner / HTTP envelope.

Human-readable ``message`` text may evolve. Integrations MUST branch on ``code``,
not on message wording. Direct ``FinancialInput`` / ``FinancialModel`` construction
still raises Pydantic ``ValidationError``; this module is for ``run_function`` and HTTP.
"""

from __future__ import annotations

from math import isfinite
from typing import Any

from pydantic import ValidationError

MISSING_REQUIRED = "missing_required"
UNKNOWN_FIELD = "unknown_field"
NULL_NOT_ALLOWED = "null_not_allowed"
NEGATIVE_VALUE = "negative_value"
INVALID_TYPE = "invalid_type"
NON_FINITE_VALUE = "non_finite_value"
UNKNOWN_CALCULATION = "unknown_calculation"

ERROR_CODES = (
    MISSING_REQUIRED,
    UNKNOWN_FIELD,
    NULL_NOT_ALLOWED,
    NEGATIVE_VALUE,
    INVALID_TYPE,
    NON_FINITE_VALUE,
    UNKNOWN_CALCULATION,
)

_MSG_MUST_BE_NUMBER = "must be a number"
_MSG_MUST_BE_FINITE = "must be a finite number"
_MSG_MUST_BE_GE_ZERO = "must be greater than or equal to 0"
_MSG_NULL = "null is not a valid value"


def issue(
    code: str,
    message: str,
    *,
    field: str | None = None,
    value: Any = None,
    details: dict[str, Any] | None = None,
    include_value: bool = False,
) -> dict[str, Any]:
    """Build one structured issue. Omit irrelevant keys."""
    item: dict[str, Any] = {"code": code, "message": message}
    if field is not None:
        item["field"] = field
    if include_value:
        item["value"] = value
    if details:
        item["details"] = details
    return item


def _sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (item.get("field") or "", item["code"])


def sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(issues, key=_sort_key)


def attach_issues(envelope: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sort_issues(issues)
    if not ordered:
        raise ValueError("structured failure requires at least one issue")
    envelope["error"] = ordered[0]
    envelope["errors"] = ordered
    return envelope


def unknown_calculation_envelope(name: str) -> dict[str, Any]:
    message = f"Unknown function: {name}"
    return attach_issues(
        {"status": "error", "message": message},
        [issue(UNKNOWN_CALCULATION, message)],
    )


def invalid_inputs_envelope(function: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    return attach_issues(
        {
            "status": "error",
            "function": function,
            "message": "One or more values are invalid.",
        },
        issues,
    )


def non_object_envelope(function: str) -> dict[str, Any]:
    message = "Inputs must be a JSON object of field names to numbers."
    return attach_issues(
        {"status": "error", "function": function, "message": message},
        [issue(INVALID_TYPE, message)],
    )


def unknown_field_issues(keys: list[str]) -> list[dict[str, Any]]:
    return [
        issue(UNKNOWN_FIELD, f"{key} is not an accepted field", field=key)
        for key in keys
    ]


def null_not_allowed_issues(keys: list[str]) -> list[dict[str, Any]]:
    return [
        issue(
            NULL_NOT_ALLOWED,
            f"{key} must not be null",
            field=key,
            value=None,
            include_value=True,
        )
        for key in keys
    ]


def missing_required_issues(keys: list[str]) -> list[dict[str, Any]]:
    return [
        issue(MISSING_REQUIRED, f"{key} is required", field=key) for key in keys
    ]


def _ctx_error_text(err: dict[str, Any]) -> str:
    ctx = err.get("ctx") or {}
    raw = ctx.get("error")
    if raw is None:
        msg = err.get("msg") or ""
        prefix = "Value error, "
        return msg[len(prefix) :] if msg.startswith(prefix) else msg
    return str(raw)


def _field_from_loc(loc: tuple[Any, ...] | list[Any]) -> str | None:
    parts = [str(part) for part in loc if part != "body"]
    return parts[-1] if parts else None


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, float) and not isfinite(value):
        return str(value)
    return value


def map_validation_error(exc: ValidationError) -> list[dict[str, Any]]:
    """Map Pydantic errors from NonNegativeNumber validators to stable codes."""
    issues: list[dict[str, Any]] = []
    for err in exc.errors():
        field = _field_from_loc(err.get("loc") or ())
        text = _ctx_error_text(err)
        raw_input = err.get("input")
        safe_value = _json_safe_value(raw_input)

        if text == _MSG_NULL:
            issues.append(
                issue(
                    NULL_NOT_ALLOWED,
                    f"{field} must not be null" if field else text,
                    field=field,
                    value=None,
                    include_value=True,
                )
            )
        elif text == _MSG_MUST_BE_NUMBER:
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} must be a number" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                )
            )
        elif text == _MSG_MUST_BE_FINITE:
            issues.append(
                issue(
                    NON_FINITE_VALUE,
                    f"{field} must be a finite number" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                )
            )
        elif text == _MSG_MUST_BE_GE_ZERO:
            issues.append(
                issue(
                    NEGATIVE_VALUE,
                    f"{field} must be greater than or equal to 0" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 0},
                )
            )
        else:
            raise ValueError(
                f"unmapped validation error for structured contract: "
                f"field={field!r} text={text!r} type={err.get('type')!r}"
            )
    return issues
