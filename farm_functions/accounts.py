"""Accounting views: net profit (ADR-0038) and balance sheet (ADR-0039).

Application layer: bridges Operating Surplus to net profit before tax, and
builds the balance sheet from Platform balances plus loans and the asset
register (split / valued here, so the Platform never sums money).
"""

from __future__ import annotations

from typing import Any

from farm_functions.assets import month_index, nbv_at
from farm_functions.compare import pl_statements
from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.loans import amortisation_schedule
from farm_functions.core.ratios import coverage_ratio, per_unit
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


def _loans_split(loans: list[dict[str, Any]], as_of: int) -> tuple[float, float]:
    """(total balance, principal due within 12 months of the balance sheet date)."""
    balance = due = 0.0
    for loan in loans:
        balance += loan["balance"]
        first = month_index(loan["year"], loan["month"])
        rows = amortisation_schedule(loan["balance"], loan["annual_rate"], loan["remaining_months"])
        due += sum(row["principal"] for i, row in enumerate(rows) if first + i <= as_of + 12)
    return balance, due


def _pct(part: float, whole: float) -> float | None:
    value = per_unit(part, whole)
    return None if value is None else round_margin_pct(value * 100)


def bs_summary(
    *,
    year: int,
    month: int,
    cash: float = 0.0,
    debtors: float = 0.0,
    stock: float = 0.0,
    livestock: float = 0.0,
    land: float = 0.0,
    creditors: float = 0.0,
    other_long_term_liabilities: float = 0.0,
    loans: list[dict[str, Any]] | None = None,
    assets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """``bs.summary``: balance sheet at month end, net worth and ratios."""
    as_of = month_index(year, month)
    fixed = {"buildings": 0.0, "machinery": 0.0, "other": 0.0}
    for asset in assets or []:
        if month_index(asset["year"], asset["month"]) <= as_of:
            fixed[asset["category"]] += nbv_at(asset, as_of)
    loan_balance, loans_due = _loans_split(loans or [], as_of)

    current_assets = {"cash": max(cash, 0.0), "debtors": debtors, "stock": stock}
    non_current_assets = {
        "land": land,
        "buildings": fixed["buildings"],
        "machinery": fixed["machinery"],
        "other_fixed_assets": fixed["other"],
        "livestock": livestock,
    }
    current_liabilities = {
        "overdraft": max(-cash, 0.0),
        "creditors": creditors,
        "loans_due_within_12_months": loans_due,
    }
    non_current_liabilities = {
        "loans_due_after_12_months": loan_balance - loans_due,
        "other_long_term_liabilities": other_long_term_liabilities,
    }

    def section(lines: dict[str, float]) -> dict[str, float]:
        rounded = {k: round_money(v) for k, v in lines.items()}
        return {**rounded, "total": round_money(sum(rounded.values()))}

    ca, nca = section(current_assets), section(non_current_assets)
    cl, ncl = section(current_liabilities), section(non_current_liabilities)
    total_assets = round_money(ca["total"] + nca["total"])
    total_liabilities = round_money(cl["total"] + ncl["total"])
    net_worth = round_money(total_assets - total_liabilities)
    current_ratio = coverage_ratio(ca["total"], cl["total"])
    return {
        "currency": "EUR",
        "as_of": {"kind": "month", "year": year, "month": month},
        "assets": {"current": ca, "non_current": nca, "total": total_assets},
        "liabilities": {"current": cl, "non_current": ncl, "total": total_liabilities},
        "net_worth": net_worth,
        "ratios": {
            "equity_pct": _pct(net_worth, total_assets),
            "debt_to_assets_pct": _pct(total_liabilities, total_assets),
            # Livestock is excluded on purpose: selling the herd is not liquidity.
            "current_ratio": None if current_ratio is None else round_money(current_ratio),
            "working_capital": round_money(ca["total"] - cl["total"]),
        },
    }
