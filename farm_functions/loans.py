"""Loan schedules and debt capacity (ADR-0025, ADR-0036).

Application layer: attaches calendar periods to Core amortisation rows, totals
the portfolio, and sizes the largest affordable new loan, so the Platform never
sums money.
"""

from __future__ import annotations

from math import floor
from typing import Any

from farm_functions.compare import pl_statements
from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.loans import amortisation_schedule, annuity_payment, annuity_principal
from farm_functions.core.ratios import coverage_ratio
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


def debt_capacity(
    *,
    months: list[dict[str, Any]],
    annual_rate: float,
    term_months: int,
    drawings: float = 0.0,
    tax: float = 0.0,
    off_farm_income: float = 0.0,
    min_cover: float = 1.0,
) -> dict[str, Any]:
    """``debt.capacity``: repayment capacity, cover and the largest new loan (ADR-0036)."""
    statements = pl_statements(months)
    surplus = sum_amounts(*(s["profit"]["net"] for s in statements))
    debt_service = sum_amounts(*(s["finance"]["loan_repayments"] for s in statements))
    capacity = surplus + off_farm_income - drawings - tax
    # Total debt service the lender accepts: capacity / required cover.
    headroom = max(0.0, capacity / min_cover - debt_service)
    monthly_payment = headroom / len(statements)
    # Round the loan down so its instalment never exceeds the headroom.
    max_loan = floor(annuity_principal(monthly_payment, annual_rate, term_months) * 100) / 100
    cover = coverage_ratio(capacity, debt_service)
    periods = sorted((s["period"]["year"], s["period"]["month"]) for s in statements)
    return {
        "currency": "EUR",
        "from": {"kind": "month", "year": periods[0][0], "month": periods[0][1]},
        "to": {"kind": "month", "year": periods[-1][0], "month": periods[-1][1]},
        "month_count": len(statements),
        "surplus": round_money(surplus),
        "off_farm_income": round_money(off_farm_income),
        "drawings": round_money(drawings),
        "tax": round_money(tax),
        "repayment_capacity": round_money(capacity),
        "debt_service": round_money(debt_service),
        "repayment_cover": None if cover is None else round_money(cover),
        "min_cover": min_cover,
        "new_loan": {
            "annual_rate": annual_rate,
            "term_months": term_months,
            "max_monthly_payment": round_money(monthly_payment),
            "max_principal": max_loan,
            "monthly_payment_at_max": round_money(annuity_payment(max_loan, annual_rate, term_months)),
        },
    }
