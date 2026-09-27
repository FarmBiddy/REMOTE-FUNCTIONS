"""P1.3 — annual and monthly share canonical financial primitives.

Proves two period compositions over one financial semantics stack.
Does not derive monthly reference values from the annual €240k farm.
"""

from __future__ import annotations

import ast
from pathlib import Path

from farm_functions.agriculture.revenue import scheme_revenue
from farm_functions.core.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct
from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES, total_costs
from farm_functions.dairy.monthly_statement import monthly_pl_summary
from farm_functions.dairy.revenue import other_revenue
from farm_functions.dairy.statement import pl_summary
from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    calculate_annual_pnl,
    calculate_monthly_dairy_statement,
)
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.schemas import MonthlyDairyFinancialInput

REPO = Path(__file__).resolve().parents[1]
DAIRY = REPO / "farm_functions" / "dairy"

# Monthly reference (explicit monthly inputs — not annual ÷ 12).
MONTHLY_REFERENCE_INPUTS = {
    "milk_litres": 40_000,
    "milk_price": 0.40,
    "biss": 2_000,
    "acres": 500,
    "other_grants": 0,
    "cattle_sales": 1_000,
    "land_leasing_income": 0,
    "other": 0,
    "feed": 5_000,
    "fertiliser": 1_000,
    "loan_repayments": 1_500,
}


def _imported_from(path: Path) -> dict[str, set[str]]:
    """Map module → set of imported names from that module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    by_module: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = {alias.name for alias in node.names if alias.name != "*"}
            by_module.setdefault(node.module, set()).update(names)
    return by_module


def _monthly_model(
    year: int = 2026,
    month: int = 3,
    **input_overrides,
) -> MonthlyDairyStatementModel:
    data = {**MONTHLY_REFERENCE_INPUTS, **input_overrides}
    return MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=year, month=month),
        inputs=MonthlyDairyFinancialInput.model_validate(data),
    )


def _financial_snapshot(result) -> dict:
    return {
        "currency": result.currency,
        "revenue": result.revenue.model_dump(),
        "costs": result.costs.model_dump(),
        "profit": result.profit.model_dump(),
        "finance": result.finance.model_dump(),
    }


def test_annual_and_monthly_statements_import_same_core_primitives() -> None:
    annual_imports = _imported_from(DAIRY / "statement.py")
    monthly_imports = _imported_from(DAIRY / "monthly_statement.py")
    core_surplus = {
        "net_profit",
        "profit_margin",
        "profit_margin_pct",
    }
    core_rounding = {
        "round_money",
        "round_margin_ratio",
        "round_margin_pct",
    }
    assert core_surplus <= annual_imports["farm_functions.core.surplus"]
    assert core_surplus <= monthly_imports["farm_functions.core.surplus"]
    assert core_rounding <= annual_imports["farm_functions.core.rounding"]
    assert core_rounding <= monthly_imports["farm_functions.core.rounding"]
    # Runtime identity of the shared callables.
    assert net_profit is pl_summary.__globals__["net_profit"]
    assert net_profit is monthly_pl_summary.__globals__["net_profit"]
    assert profit_margin is pl_summary.__globals__["profit_margin"]
    assert profit_margin is monthly_pl_summary.__globals__["profit_margin"]
    assert profit_margin_pct is pl_summary.__globals__["profit_margin_pct"]
    assert profit_margin_pct is monthly_pl_summary.__globals__["profit_margin_pct"]
    assert round_money is pl_summary.__globals__["round_money"]
    assert round_money is monthly_pl_summary.__globals__["round_money"]


def test_annual_and_monthly_share_cost_catalogue_and_total_costs() -> None:
    assert OPERATING_COST_CATEGORIES is pl_summary.__globals__["OPERATING_COST_CATEGORIES"]
    assert OPERATING_COST_CATEGORIES is monthly_pl_summary.__globals__["OPERATING_COST_CATEGORIES"]
    assert total_costs is pl_summary.__globals__["total_costs"]
    assert total_costs is monthly_pl_summary.__globals__["total_costs"]
    assert "water" in OPERATING_COST_CATEGORIES
    assert "loan_repayments" not in OPERATING_COST_CATEGORIES


def test_annual_and_monthly_share_scheme_and_other_revenue() -> None:
    assert scheme_revenue is pl_summary.__globals__["scheme_revenue"]
    assert scheme_revenue is monthly_pl_summary.__globals__["scheme_revenue"]
    assert other_revenue is pl_summary.__globals__["other_revenue"]
    assert other_revenue is monthly_pl_summary.__globals__["other_revenue"]
    assert scheme_revenue(biss=2_000, acres=500) == 2_500


def test_loan_repayments_outside_operating_math_both_periods() -> None:
    annual_base = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    annual_high = calculate_annual_pnl(
        FinancialModel(
            inputs=FinancialInput.model_validate(
                {**load_sample_inputs(), "loan_repayments": 99_999}
            )
        )
    )
    assert annual_high.finance.loan_repayments == 99_999.0
    assert annual_high.costs.total == annual_base.costs.total
    assert annual_high.profit.net == annual_base.profit.net
    assert annual_high.profit.margin == annual_base.profit.margin
    assert annual_high.profit.margin_pct == annual_base.profit.margin_pct
    assert "loan_repayments" not in annual_base.costs.lines.model_dump()

    monthly_base = calculate_monthly_dairy_statement(_monthly_model())
    monthly_high = calculate_monthly_dairy_statement(
        _monthly_model(loan_repayments=9_999)
    )
    assert monthly_high.finance.loan_repayments == 9_999.0
    assert monthly_high.costs.total == monthly_base.costs.total
    assert monthly_high.profit.net == monthly_base.profit.net
    assert monthly_high.profit.margin == monthly_base.profit.margin
    assert monthly_high.profit.margin_pct == monthly_base.profit.margin_pct


def test_shared_rounding_policy_on_equal_raw_totals() -> None:
    """Same raw totals publish identically via Core rounding on both paths."""
    revenue, costs = 19_500.0, 6_000.0
    surplus = net_profit(revenue, costs)
    published = {
        "net": round_money(surplus),
        "margin": round_margin_ratio(profit_margin(revenue, costs)),
        "margin_pct": round_margin_pct(profit_margin_pct(revenue, costs)),
        "revenue_total": round_money(revenue),
        "costs_total": round_money(costs),
    }
    monthly = calculate_monthly_dairy_statement(_monthly_model())
    assert monthly.profit.net == published["net"]
    assert monthly.profit.margin == published["margin"]
    assert monthly.profit.margin_pct == published["margin_pct"]
    assert monthly.revenue.total == published["revenue_total"]
    assert monthly.costs.total == published["costs_total"]

    # Equal raw totals through Core must match annual publish path for those totals.
    assert round_money(240_000) == 240_000.0
    assert round_money(163_000) == 163_000.0
    assert round_money(77_000) == 77_000.0
    assert round_margin_ratio(77_000 / 240_000) == 0.3208
    assert round_margin_pct((77_000 / 240_000) * 100) == 32.08


def test_period_identity_does_not_affect_financial_arithmetic() -> None:
    march = calculate_monthly_dairy_statement(_monthly_model(year=2026, month=3))
    april = calculate_monthly_dairy_statement(_monthly_model(year=2026, month=4))
    assert march.period.model_dump() == {"kind": "month", "year": 2026, "month": 3}
    assert april.period.model_dump() == {"kind": "month", "year": 2026, "month": 4}
    assert _financial_snapshot(march) == _financial_snapshot(april)


def test_annual_reference_freeze() -> None:
    annual = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    assert annual.period == "annual"
    assert annual.revenue.total == 240_000.0
    assert annual.revenue.schemes == 25_000.0
    assert annual.costs.total == 163_000.0
    assert annual.profit.net == 77_000.0
    assert annual.profit.margin == 0.3208
    assert annual.profit.margin_pct == 32.08
    assert annual.finance.loan_repayments == 12_000.0


def test_monthly_reference_freeze() -> None:
    result = calculate_monthly_dairy_statement(_monthly_model(year=2026, month=3))
    assert result.period.model_dump() == {"kind": "month", "year": 2026, "month": 3}
    assert result.revenue.milk == 16_000.0
    assert result.revenue.schemes == 2_500.0
    assert result.revenue.other == 1_000.0
    assert result.revenue.total == 19_500.0
    assert result.costs.total == 6_000.0
    assert result.profit.net == 13_500.0
    assert result.profit.margin == 0.6923
    assert result.profit.margin_pct == 69.23
    assert result.finance.loan_repayments == 1_500.0


def test_monthly_input_change_moves_result_without_annual_allocation() -> None:
    """Strongest no-÷12 evidence: explicit monthly drivers move monthly totals."""
    base = calculate_monthly_dairy_statement(_monthly_model())
    more_milk = calculate_monthly_dairy_statement(_monthly_model(milk_litres=50_000))
    assert more_milk.revenue.milk == 20_000.0
    assert more_milk.revenue.total == base.revenue.total + 4_000.0
    assert more_milk.profit.net == base.profit.net + 4_000.0

    more_feed = calculate_monthly_dairy_statement(_monthly_model(feed=6_000))
    assert more_feed.costs.total == 7_000.0
    assert more_feed.profit.net == base.profit.net - 1_000.0

    annual = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    assert annual.revenue.total == 240_000.0
    assert annual.profit.net == 77_000.0
