"""Dairy KPI summary over a set of months (ADR-0028, ADR-0032, ADR-0033).

Application layer: runs the normal monthly statements, totals them, then hands
the totals to the Dairy KPI composition.
"""

from __future__ import annotations

from typing import Any, Callable

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.rounding import round_money
from farm_functions.dairy.kpis import dairy_kpis
from farm_functions.domain import (
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    MultiMonthDairyStatementModel,
    calculate_multi_month_dairy_statements,
)
from farm_functions.schemas import MonthlyDairyFinancialInput


def kpi_summary(
    *,
    months: list[dict[str, Any]],
    milking_cows: float,
    milk_solids_kg: float | None = None,
    hectares: float | None = None,
    debt_balance: float | None = None,
) -> dict[str, Any]:
    """Run the monthly statements, total them, then derive Dairy KPIs (ADR-0028)."""
    statements = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(
            months=[
                MonthlyDairyStatementModel(
                    period=MonthlyPeriodIdentity(year=item["year"], month=item["month"]),
                    inputs=MonthlyDairyFinancialInput.model_validate(
                        {k: v for k, v in item.items() if k not in ("year", "month")}
                    ),
                )
                for item in months
            ]
        )
    ).model_dump()["months"]

    def total(pick: Callable[[dict[str, Any]], float]) -> float:
        return sum_amounts(*(pick(s) for s in statements))

    totals = {
        "milk_litres": sum_amounts(*(item["milk_litres"] for item in months)),
        "revenue": total(lambda s: s["revenue"]["total"]),
        "costs": total(lambda s: s["costs"]["total"]),
        "surplus": total(lambda s: s["profit"]["net"]),
        "loan_repayments": total(lambda s: s["finance"]["loan_repayments"]),
    }
    cost_lines = {
        name: total(lambda s, name=name: s["costs"]["lines"][name])
        for name in statements[0]["costs"]["lines"]
    }
    return {
        "currency": "EUR",
        "from": statements[0]["period"],
        "to": statements[-1]["period"],
        "month_count": len(statements),
        "milking_cows": milking_cows,
        "totals": {name: round_money(value) for name, value in totals.items()},
        **dairy_kpis(
            milking_cows=milking_cows,
            cost_lines=cost_lines,
            milk_solids_kg=milk_solids_kg,
            hectares=hectares,
            debt_balance=debt_balance,
            **totals,
        ),
    }
