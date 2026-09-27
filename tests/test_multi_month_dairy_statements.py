"""P2.1 multi-month Domain composition over existing monthly calculator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    MultiMonthDairyStatementModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    calculate_annual_pnl,
    calculate_monthly_dairy_statement,
    calculate_multi_month_dairy_statements,
)
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.schemas import MonthlyDairyFinancialInput

# Locked March 2026 monthly reference (not annual ÷ 12).
MARCH_2026_INPUTS = {
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


def _month(
    year: int,
    month: int,
    **input_overrides,
) -> MonthlyDairyStatementModel:
    data = {**MARCH_2026_INPUTS, **input_overrides}
    return MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=year, month=month),
        inputs=MonthlyDairyFinancialInput.model_validate(data),
    )


def test_single_month_matches_existing_monthly_calculator() -> None:
    envelope = _month(2026, 3)
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[envelope])
    )
    single = calculate_monthly_dairy_statement(envelope)
    assert len(multi.months) == 1
    assert multi.months[0] == single
    assert multi.months[0].revenue.total == 19_500.0
    assert multi.months[0].profit.net == 13_500.0


def test_several_months_each_match_single_month_calc() -> None:
    jan = _month(2026, 1, milk_litres=10_000, biss=0, acres=0, cattle_sales=0, feed=0, fertiliser=0)
    feb = _month(2026, 2, milk_litres=20_000, biss=0, acres=0, cattle_sales=0, feed=1_000, fertiliser=0)
    mar = _month(2026, 3)
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[jan, feb, mar])
    )
    assert len(multi.months) == 3
    for item in (jan, feb, mar):
        expected = calculate_monthly_dairy_statement(item)
        got = next(
            r
            for r in multi.months
            if r.period.year == item.period.year and r.period.month == item.period.month
        )
        assert got == expected


def test_financially_different_months_remain_independent() -> None:
    low = _month(
        2026,
        1,
        milk_litres=10_000,
        milk_price=0.40,
        biss=0,
        acres=0,
        cattle_sales=0,
        feed=0,
        fertiliser=0,
        loan_repayments=0,
    )
    high = _month(
        2026,
        2,
        milk_litres=50_000,
        milk_price=0.40,
        biss=0,
        acres=0,
        cattle_sales=0,
        feed=0,
        fertiliser=0,
        loan_repayments=0,
    )
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[low, high])
    )
    assert multi.months[0].revenue.milk == 4_000.0
    assert multi.months[1].revenue.milk == 20_000.0
    assert multi.months[0].profit.net != multi.months[1].profit.net


def test_sparse_months_accepted() -> None:
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[_month(2026, 1), _month(2026, 3)])
    )
    assert [m.period.month for m in multi.months] == [1, 3]


def test_cross_year_months_accepted() -> None:
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[_month(2025, 12), _month(2026, 1)])
    )
    assert [(m.period.year, m.period.month) for m in multi.months] == [
        (2025, 12),
        (2026, 1),
    ]


def test_duplicate_year_month_rejected() -> None:
    with pytest.raises(ValidationError):
        MultiMonthDairyStatementModel(months=[_month(2026, 3), _month(2026, 3)])


def test_empty_collection_rejected() -> None:
    with pytest.raises(ValidationError):
        MultiMonthDairyStatementModel(months=[])


def test_invalid_individual_monthly_input_rejected() -> None:
    with pytest.raises(ValidationError):
        MultiMonthDairyStatementModel.model_validate(
            {
                "months": [
                    {
                        "period": {"year": 2026, "month": 3},
                        "inputs": {"milk_price": 0.40},  # missing milk_litres
                    }
                ]
            }
        )


def test_result_order_is_chronological_regardless_of_input_order() -> None:
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(
            months=[_month(2026, 3), _month(2025, 11), _month(2026, 1)]
        )
    )
    assert [(m.period.year, m.period.month) for m in multi.months] == [
        (2025, 11),
        (2026, 1),
        (2026, 3),
    ]


def test_input_model_not_mutated() -> None:
    months = [_month(2026, 3), _month(2026, 1)]
    model = MultiMonthDairyStatementModel(months=months)
    before = model.model_dump()
    calculate_multi_month_dairy_statements(model)
    assert model.model_dump() == before
    assert [m.period.month for m in model.months] == [3, 1]


def test_finance_separation_per_month() -> None:
    base = _month(2026, 3, loan_repayments=1_500)
    high = _month(2026, 3, loan_repayments=9_999)
    # Use different months so both can be in one collection.
    high = _month(2026, 4, loan_repayments=9_999)
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[base, high])
    )
    mar = multi.months[0]
    apr = multi.months[1]
    assert mar.finance.loan_repayments == 1_500.0
    assert apr.finance.loan_repayments == 9_999.0
    assert mar.costs.total == apr.costs.total
    assert mar.profit.net == apr.profit.net
    assert mar.profit.margin == apr.profit.margin
    assert "loan_repayments" not in mar.costs.lines.model_dump()


def test_no_ytd_or_aggregate_fields_on_result() -> None:
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[_month(2026, 3)])
    )
    dumped = multi.model_dump()
    assert set(dumped.keys()) == {"currency", "months"}
    assert "ytd" not in dumped
    assert "total" not in dumped
    assert "totals" not in dumped


def test_annual_and_monthly_references_unchanged() -> None:
    annual = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    assert annual.revenue.total == 240_000.0
    assert annual.costs.total == 163_000.0
    assert annual.profit.net == 77_000.0
    assert annual.profit.margin == 0.3208
    assert annual.profit.margin_pct == 32.08
    assert annual.finance.loan_repayments == 12_000.0

    monthly = calculate_monthly_dairy_statement(_month(2026, 3))
    assert monthly.revenue.total == 19_500.0
    assert monthly.costs.total == 6_000.0
    assert monthly.profit.net == 13_500.0
    assert monthly.profit.margin == 0.6923
    assert monthly.profit.margin_pct == 69.23
    assert monthly.finance.loan_repayments == 1_500.0
