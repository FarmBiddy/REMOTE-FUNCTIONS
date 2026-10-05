"""Variance analysis: actual vs comparison months (ADR-0035).

Application layer: runs the normal monthly statements for both sets, totals
every money line, and reports actual, comparison, change and change %.
"""

from __future__ import annotations

from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.ratios import per_unit
from farm_functions.core.rounding import round_margin_pct, round_money
from farm_functions.core.surplus import profit_margin_pct
from farm_functions.core.variance import change_pct, price_volume_effects
from farm_functions.domain import (
    MonthlyDairyCashFlowModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    calculate_monthly_dairy_cash_flow,
    calculate_monthly_dairy_statement,
)
from farm_functions.schemas import MonthlyDairyCashFlowInput, MonthlyDairyFinancialInput

_PERIOD_KEYS = ("year", "month")
# Statement keys that are not summable money (identity, ratios, positions).
_SKIP = {"currency", "period", "margin", "margin_pct", "opening_cash", "closing_cash"}


def _split(item: dict[str, Any]) -> tuple[MonthlyPeriodIdentity, dict[str, float]]:
    lines = {k: v for k, v in item.items() if k not in _PERIOD_KEYS}
    return MonthlyPeriodIdentity(year=item["year"], month=item["month"]), lines


def _sum_trees(trees: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum every money leaf across statements with the same shape."""
    out: dict[str, Any] = {}
    for key, value in trees[0].items():
        if key in _SKIP:
            continue
        if isinstance(value, dict):
            out[key] = _sum_trees([t[key] for t in trees])
        else:
            out[key] = sum_amounts(*(t[key] for t in trees))
    return out


def _variance_tree(actual: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, a in actual.items():
        c = comparison[key]
        if isinstance(a, dict):
            out[key] = _variance_tree(a, c)
        else:
            pct = change_pct(a, c)
            out[key] = {
                "actual": round_money(a),
                "comparison": round_money(c),
                "change": round_money(a - c),
                "change_pct": None if pct is None else round_margin_pct(pct),
            }
    return out


def _span(statements: list[dict[str, Any]]) -> dict[str, Any]:
    periods = sorted(statements, key=lambda s: (s["period"]["year"], s["period"]["month"]))
    return {"from": periods[0]["period"], "to": periods[-1]["period"], "month_count": len(periods)}


def pl_statements(months: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in months:
        period, lines = _split(item)
        model = MonthlyDairyStatementModel(
            period=period, inputs=MonthlyDairyFinancialInput.model_validate(lines)
        )
        out.append(calculate_monthly_dairy_statement(model).model_dump())
    return out


def _cf_statements(months: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in months:
        period, lines = _split(item)
        model = MonthlyDairyCashFlowModel(
            period=period, inputs=MonthlyDairyCashFlowInput.model_validate(lines)
        )
        out.append(calculate_monthly_dairy_cash_flow(model).model_dump())
    return out


def compare_pl(*, actual: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> dict[str, Any]:
    """``pl.compare``: line-by-line P&L variance plus milk price / volume effects."""
    a_stmts, c_stmts = pl_statements(actual), pl_statements(comparison)
    a_tot, c_tot = _sum_trees(a_stmts), _sum_trees(c_stmts)

    a_litres = sum_amounts(*(m["milk_litres"] for m in actual))
    c_litres = sum_amounts(*(m["milk_litres"] for m in comparison))
    a_price = per_unit(a_tot["revenue"]["milk"], a_litres) or 0.0
    c_price = per_unit(c_tot["revenue"]["milk"], c_litres) or 0.0
    volume, price = price_volume_effects(a_litres, a_price, c_litres, c_price)

    def margin(tot: dict[str, Any]) -> float:
        return profit_margin_pct(tot["revenue"]["total"], tot["costs"]["total"])

    # Published (rounded) margins, so actual − comparison = change_pp on screen.
    a_margin, c_margin = round_margin_pct(margin(a_tot)), round_margin_pct(margin(c_tot))
    return {
        "currency": "EUR",
        "actual": _span(a_stmts),
        "comparison": _span(c_stmts),
        **_variance_tree(a_tot, c_tot),
        "margin_pct": {
            "actual": a_margin,
            "comparison": c_margin,
            "change_pp": round_margin_pct(a_margin - c_margin),
        },
        "milk": {
            "litres": _variance_tree({"v": a_litres}, {"v": c_litres})["v"],
            "price_c": {
                "actual": round_money(a_price * 100),
                "comparison": round_money(c_price * 100),
                "change": round_money((a_price - c_price) * 100),
            },
            "volume_effect": round_money(volume),
            "price_effect": round_money(price),
        },
    }


def compare_cf(*, actual: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> dict[str, Any]:
    """``cf.compare``: line-by-line cash flow variance (movements only, no balances)."""
    a_stmts, c_stmts = _cf_statements(actual), _cf_statements(comparison)
    return {
        "currency": "EUR",
        "actual": _span(a_stmts),
        "comparison": _span(c_stmts),
        **_variance_tree(_sum_trees(a_stmts), _sum_trees(c_stmts)),
    }
