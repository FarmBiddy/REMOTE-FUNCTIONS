"""Monthly Dairy Cash Flow composition (P3.2).

Calendar-blind: explicit cash floats only. Period identity is stamped by Domain.

``CASH_FLOW_CATALOGUE`` is the single Dairy cash catalogue: each line belongs to
one activity (operating / investing / financing) and one direction (in / out).
Operating line names are the **same category IDs as the P&L** (ADR-0023), so one
tagged invoice line can feed both statements: accrual date → P&L, payment date
→ Cash Flow. Amounts are never derived from P&L (ADR-0022).

Placement of ``interest_paid`` under financing outflows is Phase 1 Dairy policy
(D-CF1). Core only sums and nets amounts.
"""

from farm_functions.core.cash import (
    CashActivity,
    CashDirection,
    cash_section_net,
    net_cash_flow,
    sum_cash_amounts,
)
from farm_functions.core.rounding import round_money
from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES

CASH_FLOW_CATALOGUE: dict[tuple[CashActivity, CashDirection], tuple[str, ...]] = {
    ("operating", "in"): (
        "milk",
        "biss",
        "acres",
        "other_grants",
        "cattle_sales",
        "land_leasing_income",
        "other",
    ),
    ("operating", "out"): OPERATING_COST_CATEGORIES,
    ("investing", "in"): ("asset_disposal_proceeds",),
    ("investing", "out"): ("machinery_equipment_payments", "other_capital_payments"),
    ("financing", "in"): ("loan_proceeds",),
    ("financing", "out"): ("loan_principal_repayments", "interest_paid"),
}

CASH_FLOW_LINES = tuple(name for names in CASH_FLOW_CATALOGUE.values() for name in names)

OPERATING_CASH_INFLOW_CATEGORIES = CASH_FLOW_CATALOGUE[("operating", "in")]
OPERATING_CASH_OUTFLOW_CATEGORIES = CASH_FLOW_CATALOGUE[("operating", "out")]
INVESTING_CASH_INFLOW_CATEGORIES = CASH_FLOW_CATALOGUE[("investing", "in")]
INVESTING_CASH_OUTFLOW_CATEGORIES = CASH_FLOW_CATALOGUE[("investing", "out")]
FINANCING_CASH_INFLOW_CATEGORIES = CASH_FLOW_CATALOGUE[("financing", "in")]
FINANCING_CASH_OUTFLOW_CATEGORIES = CASH_FLOW_CATALOGUE[("financing", "out")]


def monthly_cash_flow(**amounts: float) -> dict:
    """Compose one monthly Dairy Cash Flow from explicit cash amounts.

    Keys are ``CASH_FLOW_LINES``; missing lines count as 0, unknown keys raise.
    Returns money payload only (no ``period`` key).
    """
    unknown = set(amounts) - set(CASH_FLOW_LINES)
    if unknown:
        raise TypeError(f"unknown cash lines: {sorted(unknown)}")
    values = {name: float(amounts.get(name, 0)) for name in CASH_FLOW_LINES}

    raw = {
        key: sum_cash_amounts(*(values[name] for name in names))
        for key, names in CASH_FLOW_CATALOGUE.items()
    }
    payload: dict = {"currency": "EUR"}
    for activity in ("operating", "investing", "financing"):
        groups = {
            direction: {
                "lines": {
                    name: round_money(values[name])
                    for name in CASH_FLOW_CATALOGUE[(activity, direction)]
                },
                "total": round_money(raw[(activity, direction)]),
            }
            for direction in ("in", "out")
        }
        payload[activity] = {
            "inflows": groups["in"],
            "outflows": groups["out"],
            "net": round_money(cash_section_net(raw[(activity, "in")], raw[(activity, "out")])),
        }
    cash_in = sum_cash_amounts(*(v for (_, d), v in raw.items() if d == "in"))
    cash_out = sum_cash_amounts(*(v for (_, d), v in raw.items() if d == "out"))
    payload["cash_in"] = round_money(cash_in)
    payload["cash_out"] = round_money(cash_out)
    payload["net_cash_flow"] = round_money(net_cash_flow(cash_in, cash_out))
    return payload


__all__ = [
    "CASH_FLOW_CATALOGUE",
    "CASH_FLOW_LINES",
    "FINANCING_CASH_INFLOW_CATEGORIES",
    "FINANCING_CASH_OUTFLOW_CATEGORIES",
    "INVESTING_CASH_INFLOW_CATEGORIES",
    "INVESTING_CASH_OUTFLOW_CATEGORIES",
    "OPERATING_CASH_INFLOW_CATEGORIES",
    "OPERATING_CASH_OUTFLOW_CATEGORIES",
    "monthly_cash_flow",
]
