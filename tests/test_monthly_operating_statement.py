"""P1.2 monthly Dairy Operating Statement characterisation.

Hand-checkable reference (explicit monthly inputs — not annual ÷ 12):

  year=2026, month=3
  milk_litres=40000, milk_price=0.40  → milk = 16000
  biss=2000, acres=500, other_grants=0 → schemes = 2500
  cattle_sales=1000 → other = 1000
  Operating Income = 19500
  feed=5000, fertiliser=1000 → costs = 6000
  Operating Surplus = 13500
  margin = 13500/19500 → published 0.6923 / 69.23%
  loan_repayments=1500 (finance only)
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

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

# Explicit monthly reference — do not derive from the annual €240k farm.
REFERENCE_PERIOD = {"kind": "month", "year": 2026, "month": 3}
REFERENCE_INPUTS = {
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


def _reference_model(**input_overrides) -> MonthlyDairyStatementModel:
    data = {**REFERENCE_INPUTS, **input_overrides}
    return MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=2026, month=3),
        inputs=MonthlyDairyFinancialInput.model_validate(data),
    )


def test_monthly_reference_hand_calculation():
    result = calculate_monthly_dairy_statement(_reference_model())
    assert result.period.model_dump() == REFERENCE_PERIOD
    assert result.currency == "EUR"
    assert result.revenue.milk == 16_000.0
    assert result.revenue.schemes == 2_500.0
    assert result.revenue.other == 1_000.0
    assert result.revenue.total == 19_500.0
    assert result.costs.total == 6_000.0
    assert result.costs.lines.feed == 5_000.0
    assert result.costs.lines.fertiliser == 1_000.0
    assert result.profit.net == 13_500.0
    assert result.profit.margin == 0.6923
    assert result.profit.margin_pct == 69.23
    assert result.finance.loan_repayments == 1_500.0
    assert "loan_repayments" not in result.costs.lines.model_dump()


def test_monthly_milk_is_litres_times_price():
    result = calculate_monthly_dairy_statement(
        _reference_model(milk_litres=10_000, milk_price=0.50, biss=0, acres=0, cattle_sales=0, feed=0, fertiliser=0)
    )
    assert result.revenue.milk == 5_000.0


def test_monthly_schemes_and_other_use_supplied_amounts():
    result = calculate_monthly_dairy_statement(
        _reference_model(
            milk_litres=0,
            milk_price=0,
            biss=100,
            acres=200,
            other_grants=50,
            cattle_sales=10,
            land_leasing_income=20,
            other=30,
            feed=0,
            fertiliser=0,
        )
    )
    assert result.revenue.milk == 0.0
    assert result.revenue.schemes == 350.0
    assert result.revenue.other == 60.0
    assert result.revenue.total == 410.0


def test_monthly_operating_costs_use_supplied_amounts():
    result = calculate_monthly_dairy_statement(
        _reference_model(
            milk_litres=0,
            milk_price=0,
            biss=0,
            acres=0,
            cattle_sales=0,
            feed=100,
            fertiliser=200,
            vet=50,
            water=25,
        )
    )
    assert result.costs.total == 375.0
    assert result.costs.lines.vet == 50.0
    assert result.costs.lines.water == 25.0


def test_operating_surplus_is_income_minus_costs():
    result = calculate_monthly_dairy_statement(_reference_model())
    assert result.profit.net == result.revenue.total - result.costs.total


def test_zero_revenue_margin_matches_core_semantics():
    result = calculate_monthly_dairy_statement(
        _reference_model(
            milk_litres=0,
            milk_price=0,
            biss=0,
            acres=0,
            cattle_sales=0,
            feed=1_000,
            fertiliser=0,
            loan_repayments=0,
        )
    )
    assert result.revenue.total == 0.0
    assert result.costs.total == 1_000.0
    assert result.profit.net == -1_000.0
    assert result.profit.margin == 0.0
    assert result.profit.margin_pct == 0.0


def test_loan_repayments_do_not_affect_operating_performance():
    base = calculate_monthly_dairy_statement(_reference_model(loan_repayments=1_500))
    high = calculate_monthly_dairy_statement(_reference_model(loan_repayments=9_999))
    assert high.finance.loan_repayments == 9_999.0
    assert high.costs.total == base.costs.total
    assert high.profit.net == base.profit.net
    assert high.profit.margin == base.profit.margin
    assert high.profit.margin_pct == base.profit.margin_pct


def test_period_identity_preserved_exactly():
    model = MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=2024, month=11),
        inputs=MonthlyDairyFinancialInput.model_validate(
            {"milk_litres": 1, "milk_price": 1}
        ),
    )
    result = calculate_monthly_dairy_statement(model)
    assert result.period.kind == "month"
    assert result.period.year == 2024
    assert result.period.month == 11


def test_explicit_zero_inputs_valid():
    result = calculate_monthly_dairy_statement(
        _reference_model(
            milk_litres=0,
            milk_price=0,
            biss=0,
            acres=0,
            cattle_sales=0,
            feed=0,
            fertiliser=0,
            loan_repayments=0,
        )
    )
    assert result.revenue.total == 0.0
    assert result.costs.total == 0.0
    assert result.profit.net == 0.0
    assert result.finance.loan_repayments == 0.0


def test_invalid_monthly_inputs_still_rejected():
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate({"milk_price": 0.40})
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate(
            {"milk_litres": 1, "milk_price": 0.40, "litres_per_cow": 5000}
        )
    with pytest.raises(ValidationError):
        MonthlyPeriodIdentity(year=2026, month=13)


def test_calculation_does_not_mutate_input_model():
    model = _reference_model()
    before = model.model_dump()
    calculate_monthly_dairy_statement(model)
    assert model.model_dump() == before


def test_annual_reference_unchanged_alongside_monthly():
    annual = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    assert annual.period == "annual"
    assert annual.revenue.total == 240_000.0
    assert annual.costs.total == 163_000.0
    assert annual.profit.net == 77_000.0
    assert annual.profit.margin == 0.3208
    assert annual.profit.margin_pct == 32.08
    assert annual.finance.loan_repayments == 12_000.0


def test_no_annual_divide_by_twelve_in_monthly_dairy_modules():
    """Monthly statement must not allocate annual values."""
    offenders: list[str] = []
    for path in (DAIRY / "monthly_statement.py", DAIRY / "revenue.py"):
        text = path.read_text(encoding="utf-8")
        for needle in ("/ 12", "/12", "÷ 12", "÷12", "annual / 12", "pro_rata", "prorata"):
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert offenders == []
