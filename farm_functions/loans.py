"""Loan schedules for one or more loans (ADR-0025).

Application layer: attaches calendar periods to Core amortisation rows and
totals the portfolio, so the Platform never sums money.
"""

from __future__ import annotations

from typing import Any

from farm_functions.core.loans import amortisation_schedule
from farm_functions.core.rounding import round_margin_pct, round_money


def _one_loan(
    *,
    balance: float,
    annual_rate: float,
    remaining_months: int,
    year: int,
    month: int,
    original_principal: float | None = None,
) -> dict[str, Any]:
    """One loan: attach calendar periods to Core amortisation rows (ADR-0025)."""
    rows = amortisation_schedule(balance, annual_rate, remaining_months)
    months = []
    for offset, row in enumerate(rows):
        index = year * 12 + month - 1 + offset
        period = {"kind": "month", "year": index // 12, "month": index % 12 + 1}
        months.append({"period": period, **row})
    repaid_pct = None
    if original_principal:
        repaid_pct = round_margin_pct((original_principal - balance) / original_principal * 100)
    return {
        "currency": "EUR",
        "balance": round_money(balance),
        "annual_rate": annual_rate,
        "remaining_months": remaining_months,
        "monthly_payment": rows[0]["payment"],
        "total_interest": round_money(sum(r["interest"] for r in rows)),
        "total_payments": round_money(sum(r["payment"] for r in rows)),
        "repaid_pct": repaid_pct,
        "months": months,
    }


def schedule_loans(*, loans: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-loan schedules plus portfolio totals and combined monthly debt service."""
    schedules = [_one_loan(**loan) for loan in loans]
    combined: dict[tuple[int, int], dict[str, float]] = {}
    for schedule in schedules:
        for row in schedule["months"]:
            key = (row["period"]["year"], row["period"]["month"])
            totals = combined.setdefault(key, {"payment": 0.0, "interest": 0.0, "principal": 0.0})
            for name in totals:
                totals[name] += row[name]
    return {
        "currency": "EUR",
        "loans": schedules,
        "total_balance": round_money(sum(s["balance"] for s in schedules)),
        "total_monthly_payment": round_money(sum(s["monthly_payment"] for s in schedules)),
        "total_interest": round_money(sum(s["total_interest"] for s in schedules)),
        "months": [
            {
                "period": {"kind": "month", "year": year, "month": month},
                **{name: round_money(value) for name, value in totals.items()},
            }
            for (year, month), totals in sorted(combined.items())
        ],
    }
