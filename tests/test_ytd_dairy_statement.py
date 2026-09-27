"""P2.2 YTD Dairy Operating Statement from explicit contiguous months."""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    MultiMonthDairyStatementModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    YtdDairyStatementModel,
    calculate_annual_pnl,
    calculate_monthly_dairy_statement,
    calculate_multi_month_dairy_statements,
    calculate_ytd_dairy_statement,
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

# Hand-checkable Jan–Mar fixture (margins where average ≠ YTD ratio).
# Jan: rev 100 / cost 10 → margin 0.90
# Feb: rev 1000 / cost 900 → margin 0.10
# Mar: rev 200 / cost 50 → margin 0.75
# Avg margins ≈ 0.583; YTD rev 1300 / cost 960 / surplus 340 / margin ≈ 0.2615
YTD_REV = 1_300.0
YTD_COST = 960.0
YTD_SURPLUS = 340.0
# Published margin uses existing banker's rounding (not raw 340/1300).
YTD_MARGIN = 0.2615
YTD_MARGIN_PCT = 26.15
AVG_MONTHLY_MARGINS = (0.90 + 0.10 + 0.75) / 3.0


def _month(year: int, month: int, **input_overrides) -> MonthlyDairyStatementModel:
    data = {**MARCH_2026_INPUTS, **input_overrides}
    return MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=year, month=month),
        inputs=MonthlyDairyFinancialInput.model_validate(data),
    )


def _hand_month(
    year: int,
    month: int,
    *,
    revenue: float,
    cost: float,
    loan: float = 0.0,
) -> MonthlyDairyStatementModel:
    """Build a month with milk-only revenue and feed-only operating cost."""
    return _month(
        year,
        month,
        milk_litres=revenue,
        milk_price=1.0,
        biss=0,
        acres=0,
        other_grants=0,
        cattle_sales=0,
        land_leasing_income=0,
        other=0,
        feed=cost,
        fertiliser=0,
        loan_repayments=loan,
    )


def _jan_mar_hand(year: int = 2026) -> list[MonthlyDairyStatementModel]:
    return [
        _hand_month(year, 1, revenue=100.0, cost=10.0, loan=5.0),
        _hand_month(year, 2, revenue=1_000.0, cost=900.0, loan=10.0),
        _hand_month(year, 3, revenue=200.0, cost=50.0, loan=15.0),
    ]


def test_jan_mar_ytd_totals_and_margin_not_average() -> None:
    result = calculate_ytd_dairy_statement(
        YtdDairyStatementModel(year=2026, as_of_month=3, months=_jan_mar_hand())
    )
    assert result.period.kind == "ytd"
    assert result.period.year == 2026
    assert result.period.as_of_month == 3
    assert result.period.months_included == [1, 2, 3]
    assert result.revenue.total == YTD_REV
    assert result.costs.total == YTD_COST
    assert result.profit.net == YTD_SURPLUS
    assert result.profit.margin == pytest.approx(YTD_MARGIN)
    assert result.profit.margin_pct == pytest.approx(YTD_MARGIN_PCT)
    assert result.profit.margin != pytest.approx(AVG_MONTHLY_MARGINS)
    assert abs(result.profit.margin - AVG_MONTHLY_MARGINS) > 0.2

    jan = calculate_monthly_dairy_statement(_hand_month(2026, 1, revenue=100.0, cost=10.0))
    feb = calculate_monthly_dairy_statement(_hand_month(2026, 2, revenue=1_000.0, cost=900.0))
    mar = calculate_monthly_dairy_statement(_hand_month(2026, 3, revenue=200.0, cost=50.0))
    assert jan.profit.margin == pytest.approx(0.90)
    assert feb.profit.margin == pytest.approx(0.10)
    assert mar.profit.margin == pytest.approx(0.75)


def test_january_only_ytd() -> None:
    jan = _hand_month(2026, 1, revenue=100.0, cost=10.0, loan=7.0)
    result = calculate_ytd_dairy_statement(
        YtdDairyStatementModel(year=2026, as_of_month=1, months=[jan])
    )
    single = calculate_monthly_dairy_statement(jan)
    assert result.period.months_included == [1]
    assert result.revenue.total == single.revenue.total
    assert result.costs.total == single.costs.total
    assert result.profit.net == single.profit.net
    assert result.profit.margin == single.profit.margin
    assert result.finance.loan_repayments == single.finance.loan_repayments


def test_loan_summed_outside_operating_surplus() -> None:
    result = calculate_ytd_dairy_statement(
        YtdDairyStatementModel(year=2026, as_of_month=3, months=_jan_mar_hand())
    )
    assert result.finance.loan_repayments == 30.0
    assert result.profit.net == YTD_SURPLUS
    assert result.costs.total == YTD_COST


def test_missing_january_rejected() -> None:
    with pytest.raises(ValidationError, match="missing months"):
        YtdDairyStatementModel(
            year=2026,
            as_of_month=2,
            months=[_hand_month(2026, 2, revenue=100.0, cost=10.0)],
        )


def test_gap_in_window_rejected() -> None:
    with pytest.raises(ValidationError, match="missing months"):
        YtdDairyStatementModel(
            year=2026,
            as_of_month=3,
            months=[
                _hand_month(2026, 1, revenue=100.0, cost=10.0),
                _hand_month(2026, 3, revenue=200.0, cost=50.0),
            ],
        )


def test_wrong_year_month_rejected() -> None:
    with pytest.raises(ValidationError, match="YTD year"):
        YtdDairyStatementModel(
            year=2026,
            as_of_month=1,
            months=[_hand_month(2025, 1, revenue=100.0, cost=10.0)],
        )


def test_duplicate_months_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        YtdDairyStatementModel(
            year=2026,
            as_of_month=1,
            months=[
                _hand_month(2026, 1, revenue=100.0, cost=10.0),
                _hand_month(2026, 1, revenue=200.0, cost=20.0),
            ],
        )


def test_invalid_as_of_month_rejected() -> None:
    with pytest.raises(ValidationError):
        YtdDairyStatementModel(
            year=2026,
            as_of_month=0,
            months=[_hand_month(2026, 1, revenue=100.0, cost=10.0)],
        )
    with pytest.raises(ValidationError):
        YtdDairyStatementModel(
            year=2026,
            as_of_month=13,
            months=[_hand_month(2026, 1, revenue=100.0, cost=10.0)],
        )


def test_months_after_as_of_ignored() -> None:
    months = _jan_mar_hand() + [_hand_month(2026, 4, revenue=9_999.0, cost=1.0, loan=999.0)]
    result = calculate_ytd_dairy_statement(
        YtdDairyStatementModel(year=2026, as_of_month=3, months=months)
    )
    assert result.period.months_included == [1, 2, 3]
    assert result.revenue.total == YTD_REV
    assert result.costs.total == YTD_COST
    assert result.profit.net == YTD_SURPLUS
    assert result.finance.loan_repayments == 30.0


def test_no_mutation_of_input_model() -> None:
    months = _jan_mar_hand()
    model = YtdDairyStatementModel(year=2026, as_of_month=3, months=months)
    before = copy.deepcopy(model.model_dump())
    calculate_ytd_dairy_statement(model)
    assert model.model_dump() == before


def test_annual_and_march_smoke_unchanged() -> None:
    annual_inputs = FinancialInput.model_validate(load_sample_inputs())
    annual = calculate_annual_pnl(FinancialModel(inputs=annual_inputs))
    assert annual.profit.net == 77_000.0
    march = calculate_monthly_dairy_statement(_month(2026, 3))
    assert march.profit.net == 13_500.0


def test_p21_sparse_still_works() -> None:
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=[_month(2026, 1), _month(2026, 3)])
    )
    assert [m.period.month for m in multi.months] == [1, 3]


def test_cost_lines_summed_by_catalogue_key() -> None:
    result = calculate_ytd_dairy_statement(
        YtdDairyStatementModel(year=2026, as_of_month=3, months=_jan_mar_hand())
    )
    assert result.costs.lines.feed == YTD_COST
    assert result.costs.lines.fertiliser == 0.0
    assert result.costs.total == YTD_COST
