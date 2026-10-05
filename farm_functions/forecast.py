"""Seasonal run-rate forecast for Dairy P&L and Cash Flow (ADR-0026).

Application layer: maps calendar months to Core period indexes, applies the
Dairy line policy, then runs the normal monthly statements on projected inputs.
"""

from __future__ import annotations

from typing import Any

from farm_functions.core.forecast import latest_non_zero, run_rate_factors, seasonal_projection
from farm_functions.core.rounding import round_margin_ratio, round_money
from farm_functions.dairy.cash_flow import CASH_FLOW_LINES
from farm_functions.dairy.forecast import (
    CASH_RECURRING_LINES,
    PL_KNOWN_ONLY_LINES,
    PL_PRICE_LINES,
)
from farm_functions.domain import (
    MonthlyDairyCashFlowModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    calculate_monthly_dairy_cash_flow,
    calculate_monthly_dairy_statement,
)
from farm_functions.schemas import MonthlyDairyCashFlowInput, MonthlyDairyFinancialInput

SEASON = 12
_PERIOD_KEYS = ("year", "month")


def _index(item: dict[str, Any]) -> int:
    return item["year"] * 12 + item["month"] - 1


def _period(index: int) -> MonthlyPeriodIdentity:
    return MonthlyPeriodIdentity(year=index // 12, month=index % 12 + 1)


def _project(
    history: list[dict[str, Any]],
    forecast: list[dict[str, Any]],
    lines: tuple[str, ...],
    recurring: tuple[str, ...],
    carried: tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, float], list[tuple[MonthlyPeriodIdentity, dict[str, float]]]]:
    """Seasonal base × run-rate, carried prices, known-only 0, then known values win."""
    actual = {
        _index(item): {k: v for k, v in item.items() if k not in _PERIOD_KEYS}
        for item in history
    }
    factors = run_rate_factors(actual, recurring, SEASON)
    projected = []
    for item in sorted(forecast, key=_index):
        target = _index(item)
        base = actual[target - SEASON]
        inputs = {line: 0.0 for line in lines}
        inputs.update(
            {line: round_money(seasonal_projection(base[line], factors[line])) for line in recurring}
        )
        inputs.update({line: latest_non_zero(actual, line) for line in carried})
        inputs.update(
            {k: v for k, v in item.items() if k not in _PERIOD_KEYS and v is not None}
        )
        projected.append((_period(target), inputs))
    as_of = _period(max(actual)).model_dump()
    return as_of, {line: round_margin_ratio(f) for line, f in factors.items()}, projected


def forecast_pl(*, history: list[dict[str, Any]], forecast: list[dict[str, Any]]) -> dict[str, Any]:
    """``pl.forecast``: projected monthly Operating Statements."""
    lines = tuple(MonthlyDairyFinancialInput.model_fields)
    recurring = tuple(l for l in lines if l not in PL_PRICE_LINES + PL_KNOWN_ONLY_LINES)
    as_of, factors, projected = _project(history, forecast, lines, recurring, PL_PRICE_LINES)
    months = [
        {
            "period": period.model_dump(),
            "inputs": inputs,
            "statement": calculate_monthly_dairy_statement(
                MonthlyDairyStatementModel(
                    period=period, inputs=MonthlyDairyFinancialInput.model_validate(inputs)
                )
            ).model_dump(),
        }
        for period, inputs in projected
    ]
    return {"currency": "EUR", "as_of": as_of, "run_rate": factors, "months": months}


def forecast_cf(*, history: list[dict[str, Any]], forecast: list[dict[str, Any]]) -> dict[str, Any]:
    """``cf.forecast``: projected monthly Cash Flows (operating lines only recur)."""
    as_of, factors, projected = _project(history, forecast, CASH_FLOW_LINES, CASH_RECURRING_LINES, ())
    months = [
        {
            "period": period.model_dump(),
            "inputs": inputs,
            "cash_flow": calculate_monthly_dairy_cash_flow(
                MonthlyDairyCashFlowModel(
                    period=period, inputs=MonthlyDairyCashFlowInput.model_validate(inputs)
                )
            ).model_dump(),
        }
        for period, inputs in projected
    ]
    return {"currency": "EUR", "as_of": as_of, "run_rate": factors, "months": months}
