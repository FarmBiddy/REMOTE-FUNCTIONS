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
UNAUTHORIZED = "unauthorized"
INVALID_JSON = "invalid_json"

ERROR_CODES = (
    MISSING_REQUIRED,
    UNKNOWN_FIELD,
    NULL_NOT_ALLOWED,
    NEGATIVE_VALUE,
    INVALID_TYPE,
    NON_FINITE_VALUE,
    UNKNOWN_CALCULATION,
    UNAUTHORIZED,
    INVALID_JSON,
)

_MSG_MUST_BE_NUMBER = "must be a number"
_MSG_MUST_BE_FINITE = "must be a finite number"
_MSG_MUST_BE_GE_ZERO = "must be greater than or equal to 0"
_MSG_NULL = "null is not a valid value"
_MSG_CALENDAR_YEAR = "must be a calendar year of 1 or greater"
_MSG_CALENDAR_MONTH = "must be a calendar month from 1 to 12"


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
    """Map Pydantic errors to stable codes (including nested / period-set)."""
    issues: list[dict[str, Any]] = []
    for err in exc.errors():
        field = _field_from_loc(err.get("loc") or ())
        text = _ctx_error_text(err)
        err_type = err.get("type") or ""
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
        elif text == _MSG_CALENDAR_YEAR:
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} must be a calendar year of 1 or greater" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 1},
                )
            )
        elif text == _MSG_CALENDAR_MONTH:
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} must be a calendar month from 1 to 12" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 1, "maximum": 12},
                )
            )
        elif err_type == "missing":
            issues.append(
                issue(
                    MISSING_REQUIRED,
                    f"{field} is required" if field else "required field is missing",
                    field=field,
                )
            )
        elif err_type in ("too_short", "list_type") and (
            field == "months" or "months" in [str(p) for p in (err.get("loc") or ())]
        ):
            # Empty months list (min_length=1) or wrong type for months.
            reason = "empty_months" if err_type == "too_short" else None
            issues.append(
                issue(
                    INVALID_TYPE,
                    "months must be a non-empty array" if err_type == "too_short" else text,
                    field="months",
                    value=safe_value,
                    include_value=True,
                    details={"reason": reason} if reason else None,
                )
            )
        elif err_type in (
            "too_short",
            "too_long",
            "list_type",
            "dict_type",
            "string_type",
            "string_too_short",
            "string_too_long",
            "literal_error",
        ):
            # Shape errors on other nested inputs (loans[], history[], scenarios[] …).
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field}: {text}" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                )
            )
        elif err_type == "extra_forbidden":
            issues.append(
                issue(
                    UNKNOWN_FIELD,
                    f"{field} is not an accepted field" if field else text,
                    field=field,
                )
            )
        elif text == "must be between 0 and 1":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} must be between 0 and 1" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 0, "maximum": 1},
                )
            )
        elif text == "must be a whole number between 1 and 600":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} {text}" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 1, "maximum": 600},
                )
            )
        elif text == "original_principal must be greater than or equal to balance":
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field="original_principal",
                    details={"reason": "principal_below_balance"},
                )
            )
        elif "duplicate" in text.lower():
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "duplicate_period"},
                )
            )
        elif text.endswith(("is required for straight_line", "is required for reducing_balance")):
            issues.append(
                issue(
                    MISSING_REQUIRED,
                    text,
                    field=text.split(" ")[0],
                    details={"reason": "method_needs_field"},
                )
            )
        elif text == "residual_value must not exceed cost":
            issues.append(
                issue(INVALID_TYPE, text, field="residual_value", details={"reason": "residual_above_cost"})
            )
        elif text == "shocks_from_year and shocks_from_month must be sent together":
            issues.append(
                issue(INVALID_TYPE, text, field="shocks_from_month", details={"reason": "incomplete_period"})
            )
        elif text == "cf_months must end in the same month as pl_months":
            issues.append(issue(INVALID_TYPE, text, field="cf_months", details={"reason": "periods_misaligned"}))
        elif text == "projected months must be after the reporting period":
            issues.append(issue(INVALID_TYPE, text, field=field, details={"reason": "projection_overlaps_period"}))
        elif text == "must be a whole number between 1 and 10":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} {text}" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 1, "maximum": 10},
                )
            )
        elif text.startswith(("assumptions have unknown lines", "annual_effects has lines")):
            issues.append(issue(UNKNOWN_FIELD, text, field=field))
        elif text == "base_pl_months must be 12 consecutive months":
            issues.append(issue(INVALID_TYPE, text, field="base_pl_months", details={"reason": "base_not_12_consecutive"}))
        elif text == "assumption lists must not be longer than years":
            issues.append(issue(INVALID_TYPE, text, field="assumptions", details={"reason": "assumption_longer_than_years"}))
        elif text == "investment year must be within years":
            issues.append(issue(INVALID_TYPE, text, field="investments", details={"reason": "investment_outside_years"}))
        elif text == "send average or monthly_average, not both":
            issues.append(issue(INVALID_TYPE, text, field="monthly_average", details={"reason": "average_conflict"}))
        elif "monthly_average has no value for" in text:
            issues.append(
                issue(INVALID_TYPE, text, field="monthly_average", details={"reason": "benchmark_months_missing"})
            )
        elif text == "bands must ascend by max_k and end with one open-ended band":
            issues.append(issue(INVALID_TYPE, text, field=field, details={"reason": "bands_invalid"}))
        elif text == "period end must not be before period start":
            issues.append(issue(INVALID_TYPE, text, field=field, details={"reason": "period_reversed"}))
        elif text == "must be above 0 and at most 100":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} {text}" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum_exclusive": 0, "maximum": 100},
                )
            )
        elif text == "must be a whole number between 1 and 40":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} {text}" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 1, "maximum": 40},
                )
            )
        elif text == "send either annual_benefit with life_years, or cash_flows":
            issues.append(issue(INVALID_TYPE, text, field=field, details={"reason": "benefit_form"}))
        elif text == "must be 1 or greater":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} must be 1 or greater" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": 1},
                )
            )
        elif text == "must be -100 or greater":
            issues.append(
                issue(
                    INVALID_TYPE,
                    f"{field} must be -100 or greater" if field else text,
                    field=field,
                    value=safe_value,
                    include_value=True,
                    details={"minimum": -100},
                )
            )
        elif text.startswith("lines_pct has lines that cannot be shocked"):
            issues.append(issue(UNKNOWN_FIELD, text, field="lines_pct"))
        elif text.startswith("monthly_effects has lines that cannot be changed"):
            issues.append(issue(UNKNOWN_FIELD, text, field="monthly_effects"))
        elif "is outside cf_months" in text:
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "investment_outside_months"},
                )
            )
        elif "must be after the last history month" in text:
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "forecast_overlaps_history"},
                )
            )
        elif "forecast needs prior-year history" in text:
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "missing_prior_year_month"},
                )
            )
        elif "months must be consecutive" in text:
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "non_contiguous_months"},
                )
            )
        elif "missing months" in text.lower():
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "ytd_incomplete"},
                )
            )
        elif "YTD year=" in text and "but month has year=" in text:
            issues.append(
                issue(
                    INVALID_TYPE,
                    text,
                    field=field,
                    details={"reason": "ytd_year_mismatch"},
                )
            )
        else:
            raise ValueError(
                f"unmapped validation error for structured contract: "
                f"field={field!r} text={text!r} type={err_type!r}"
            )
    return issues


def invalid_json_envelope(name: str) -> dict[str, Any]:
    """Body is not parseable JSON (e.g. truncated); never a server error."""
    message = "Request body is not valid JSON."
    return attach_issues(
        {"status": "error", "function": name, "message": message},
        [issue(INVALID_JSON, message)],
    )
