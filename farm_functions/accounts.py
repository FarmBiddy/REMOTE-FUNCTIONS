"""Accounting views built on the operating statements (ADR-0038).

Application layer: bridges Operating Surplus to net profit before tax using
valuation changes, depreciation and interest supplied by the caller (typically
from ``assets.schedule`` and ``loan.schedule``).
"""

from __future__ import annotations

from typing import Any

from farm_functions.compare import pl_statements
from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.ratios import per_unit
from farm_functions.core.rounding import round_margin_pct, round_money


def pl_net(
    *,
    months: list[dict[str, Any]],
    depreciation: float = 0.0,
    interest: float = 0.0,
    livestock_opening_value: float = 0.0,
    livestock_closing_value: float = 0.0,
    stock_opening_value: float = 0.0,
    stock_closing_value: float = 0.0,
) -> dict[str, Any]:
    """``pl.net``: Operating Surplus → adjusted surplus → EBIT → net profit before tax."""
    statements = pl_statements(months)
    revenue = sum_amounts(*(s["revenue"]["total"] for s in statements))
    surplus = sum_amounts(*(s["profit"]["net"] for s in statements))
    livestock_change = livestock_closing_value - livestock_opening_value
    stock_change = stock_closing_value - stock_opening_value
    adjusted = surplus + livestock_change + stock_change
    ebit = adjusted - depreciation
    net = ebit - interest
    margin = per_unit(net, revenue)
    periods = sorted((s["period"]["year"], s["period"]["month"]) for s in statements)
    return {
        "currency": "EUR",
        "from": {"kind": "month", "year": periods[0][0], "month": periods[0][1]},
        "to": {"kind": "month", "year": periods[-1][0], "month": periods[-1][1]},
        "month_count": len(statements),
        "revenue": round_money(revenue),
        "operating_surplus": round_money(surplus),
        "livestock_value_change": round_money(livestock_change),
        "stock_value_change": round_money(stock_change),
        "adjusted_surplus": round_money(adjusted),
        "depreciation": round_money(depreciation),
        "ebit": round_money(ebit),
        "interest": round_money(interest),
        "net_profit_before_tax": round_money(net),
        "net_margin_pct": None if margin is None else round_margin_pct(margin * 100),
    }
