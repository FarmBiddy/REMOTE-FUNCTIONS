"""P1.1 period domain contract characterisation (ADR-0018).

Contract and validation only — no monthly financial calculation.
"""

import pytest
from pydantic import ValidationError

from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    calculate_annual_pnl,
)
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.schemas import (
    FIELD_UNITS,
    MONTHLY_FIELD_UNITS,
    MonthlyDairyFinancialInput,
    list_monthly_dairy_input_metadata,
)

SAMPLE_MONTHLY_MILK = {
    "milk_litres": 40_000,
    "milk_price": 0.40,
}


def test_monthly_period_identity_requires_valid_calendar():
    identity = MonthlyPeriodIdentity(year=2026, month=9)
    assert identity.kind == "month"
    assert identity.year == 2026
    assert identity.month == 9
    with pytest.raises(ValidationError):
        MonthlyPeriodIdentity(year=2026, month=0)
    with pytest.raises(ValidationError):
        MonthlyPeriodIdentity(year=2026, month=13)
    with pytest.raises(ValidationError):
        MonthlyPeriodIdentity(year=0, month=1)


def test_monthly_financial_input_requires_milk_litres_and_price():
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate({"milk_price": 0.40})
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate({"milk_litres": 1000})
    parsed = MonthlyDairyFinancialInput.model_validate(SAMPLE_MONTHLY_MILK)
    assert parsed.milk_litres == 40_000
    assert parsed.milk_price == 0.40
    assert parsed.loan_repayments == 0
    assert parsed.feed == 0


def test_monthly_financial_input_rejects_annual_milk_fields():
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate(
            {**SAMPLE_MONTHLY_MILK, "milking_cows": 100}
        )
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate(
            {**SAMPLE_MONTHLY_MILK, "litres_per_cow": 5000}
        )


def test_monthly_financial_input_rejects_calendar_fields():
    """Year/month belong on the envelope, not on formula inputs."""
    with pytest.raises(ValidationError):
        MonthlyDairyFinancialInput.model_validate(
            {**SAMPLE_MONTHLY_MILK, "year": 2026, "month": 9}
        )


def test_monthly_statement_model_separates_identity_from_inputs():
    model = MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=2026, month=3),
        inputs=MonthlyDairyFinancialInput.model_validate(
            {
                **SAMPLE_MONTHLY_MILK,
                "biss": 1000,
                "feed": 5000,
                "loan_repayments": 1000,
            }
        ),
    )
    assert model.currency == "EUR"
    assert model.period.model_dump() == {"kind": "month", "year": 2026, "month": 3}
    assert "year" not in model.inputs.model_dump()
    assert "month" not in model.inputs.model_dump()
    assert model.inputs.biss == 1000
    assert model.inputs.loan_repayments == 1000


def test_monthly_statement_model_rejects_embedded_persistence_fields():
    with pytest.raises(ValidationError):
        MonthlyDairyStatementModel.model_validate(
            {
                "currency": "EUR",
                "period": {"kind": "month", "year": 2026, "month": 1},
                "inputs": SAMPLE_MONTHLY_MILK,
                "farm_id": "abc",
            }
        )


def test_monthly_metadata_units_are_period_scoped_not_per_year():
    assert MONTHLY_FIELD_UNITS["milk_litres"] == "litres"
    assert MONTHLY_FIELD_UNITS["milk_price"] == "EUR/litre"
    assert MONTHLY_FIELD_UNITS["feed"] == "EUR"
    assert "litres_per_cow" not in MONTHLY_FIELD_UNITS
    assert FIELD_UNITS["litres_per_cow"] == "litres/cow/year"
    assert FIELD_UNITS["feed"] == "EUR/year"
    names = {row["name"] for row in list_monthly_dairy_input_metadata()}
    assert "milk_litres" in names
    assert "year" not in names
    assert "month" not in names


def test_annual_financial_input_unchanged_by_monthly_contract():
    with pytest.raises(ValidationError):
        FinancialInput.model_validate(SAMPLE_MONTHLY_MILK)
    annual = FinancialInput.model_validate(
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": 0.40}
    )
    assert annual.litres_per_cow == 5000
    with pytest.raises(ValidationError):
        FinancialModel(
            period="monthly",
            currency="EUR",
            inputs=annual,
        )


def test_annual_reference_still_calculates_through_domain():
    typed = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    assert typed.period == "annual"
    assert typed.revenue.total == 240_000
    assert typed.costs.total == 163_000
    assert typed.profit.net == 77_000
    assert typed.profit.margin == 0.3208
    assert typed.profit.margin_pct == 32.08
    assert typed.finance.loan_repayments == 12_000


def test_no_monthly_calculation_entrypoint_in_domain():
    import farm_functions.domain as domain

    assert not hasattr(domain, "calculate_monthly_pnl")
    assert not hasattr(domain, "calculate_monthly_dairy_statement")
