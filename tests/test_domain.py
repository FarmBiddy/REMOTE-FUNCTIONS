import pytest
from pydantic import ValidationError

from farm_functions.calcs.summary import pl_summary
from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    FinancialResult,
    calculate_annual_pnl,
)
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.runner import run_function

SAMPLE_MILK = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
}


def test_financial_input_requires_milk_fields():
    with pytest.raises(ValidationError):
        FinancialInput.model_validate({"milking_cows": 100, "litres_per_cow": 5000})
    with pytest.raises(ValidationError):
        FinancialInput.model_validate({"milking_cows": 100, "milk_price": 0.40})
    with pytest.raises(ValidationError):
        FinancialInput.model_validate({"litres_per_cow": 5000, "milk_price": 0.40})


def test_financial_input_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        FinancialInput.model_validate({**SAMPLE_MILK, "random_field": 1})


def test_financial_input_optional_fields_default_to_zero():
    parsed = FinancialInput.model_validate(SAMPLE_MILK)
    assert parsed.biss == 0
    assert parsed.acres == 0
    assert parsed.other_grants == 0
    assert parsed.cattle_sales == 0
    assert parsed.lamb_sales == 0
    assert parsed.wool == 0
    assert parsed.other == 0
    assert parsed.feed == 0
    assert parsed.fertiliser == 0
    assert parsed.vet == 0
    assert parsed.contractor == 0
    assert parsed.labour == 0
    assert parsed.insurance == 0
    assert parsed.loan_repayments == 0
    assert parsed.fuel == 0
    assert parsed.electricity == 0


def test_financial_model_defaults_to_annual_eur():
    model = FinancialModel(inputs=FinancialInput.model_validate(SAMPLE_MILK))
    assert model.period == "annual"
    assert model.currency == "EUR"


def test_financial_model_rejects_invalid_period_and_currency():
    inputs = FinancialInput.model_validate(SAMPLE_MILK)
    with pytest.raises(ValidationError):
        FinancialModel(period="monthly", currency="EUR", inputs=inputs)
    with pytest.raises(ValidationError):
        FinancialModel(period="annual", currency="USD", inputs=inputs)


def test_financial_model_forbids_persistence_fields():
    with pytest.raises(ValidationError):
        FinancialModel.model_validate(
            {
                "period": "annual",
                "currency": "EUR",
                "inputs": SAMPLE_MILK,
                "farm_id": "abc",
            }
        )


def test_pl_summary_output_validates_as_financial_result():
    payload = pl_summary(**load_sample_inputs())
    result = FinancialResult.model_validate(payload)
    assert result.model_dump() == payload


def test_sample_pnl_results_unchanged_through_domain_types():
    payload = run_function("pl.summary", load_sample_inputs())
    assert payload["status"] == "ok"
    result = FinancialResult.model_validate(payload["result"])
    assert result.revenue.milk == 200_000
    assert result.revenue.schemes == 25_000
    assert result.revenue.other == 15_000
    assert result.revenue.total == 240_000
    assert result.costs.total == 175_000
    assert result.profit.net == 65_000
    assert result.profit.margin_pct == 27.08
    assert result.currency == "EUR"
    assert result.period == "annual"


def test_calculate_annual_pnl_matches_existing_pl_summary():
    model = FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    typed = calculate_annual_pnl(model)
    raw = pl_summary(**load_sample_inputs())
    assert typed.model_dump() == raw
    via_runner = run_function("pl.summary", load_sample_inputs())["result"]
    assert typed.model_dump() == via_runner
