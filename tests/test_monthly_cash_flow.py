"""P3.2 monthly Dairy Cash Flow characterisation.

Hand-checkable March 2026 reference (explicit cash — not P&L-derived):

  Operating In  = 18000 + 1000 + 2000 = 21000
  Operating Out = 5000 + 1000 + 500 + 500 = 7000
  Operating Net = 14000
  Investing In  = 2000
  Investing Out = 6000
  Investing Net = -4000
  Financing In  = 10000
  Financing Out = 3000 + 500 = 3500
  Financing Net = 6500
  cash_in = 33000
  cash_out = 16500
  net_cash_flow = 16500
"""

from pathlib import Path

from farm_functions.dairy.cash_flow import (
    CASH_FLOW_LINES,
    FINANCING_CASH_OUTFLOW_CATEGORIES,
    INVESTING_CASH_OUTFLOW_CATEGORIES,
    OPERATING_CASH_INFLOW_CATEGORIES,
    OPERATING_CASH_OUTFLOW_CATEGORIES,
    monthly_cash_flow,
)
from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    MonthlyDairyCashFlowModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    calculate_annual_pnl,
    calculate_monthly_dairy_cash_flow,
    calculate_monthly_dairy_statement,
)
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.schemas import (
    MonthlyDairyCashFlowInput,
    MonthlyDairyFinancialInput,
    OtherRevenueInput,
    SchemeRevenueInput,
    TotalCostsInput,
)

REPO = Path(__file__).resolve().parents[1]
DAIRY_CASH = REPO / "farm_functions" / "dairy" / "cash_flow.py"

REFERENCE_PERIOD = {"kind": "month", "year": 2026, "month": 3}
REFERENCE_INPUTS = {
    "milk": 18_000,
    "cattle_sales": 1_000,
    "biss": 2_000,
    "feed": 5_000,
    "fertiliser": 1_000,
    "vet": 500,
    "electricity": 500,
    "asset_disposal_proceeds": 2_000,
    "machinery_equipment_payments": 6_000,
    "loan_proceeds": 10_000,
    "loan_principal_repayments": 3_000,
    "interest_paid": 500,
}


def _cash_model(**overrides) -> MonthlyDairyCashFlowModel:
    data = {**REFERENCE_INPUTS, **overrides}
    return MonthlyDairyCashFlowModel(
        period=MonthlyPeriodIdentity(year=2026, month=3),
        inputs=MonthlyDairyCashFlowInput.model_validate(data),
    )


def test_monthly_cash_flow_reference_hand_calculation():
    result = calculate_monthly_dairy_cash_flow(_cash_model())
    assert result.period.model_dump() == REFERENCE_PERIOD
    assert result.currency == "EUR"

    assert result.operating.inflows.total == 21_000.0
    assert result.operating.outflows.total == 7_000.0
    assert result.operating.net == 14_000.0
    assert result.operating.inflows.lines["milk"] == 18_000.0
    assert result.operating.inflows.lines["cattle_sales"] == 1_000.0
    assert result.operating.inflows.lines["biss"] == 2_000.0

    assert result.investing.inflows.total == 2_000.0
    assert result.investing.outflows.total == 6_000.0
    assert result.investing.net == -4_000.0
    assert result.investing.outflows.lines["machinery_equipment_payments"] == 6_000.0

    assert result.financing.inflows.total == 10_000.0
    assert result.financing.outflows.total == 3_500.0
    assert result.financing.net == 6_500.0
    assert result.financing.outflows.lines["loan_principal_repayments"] == 3_000.0
    assert result.financing.outflows.lines["interest_paid"] == 500.0

    assert result.cash_in == 33_000.0
    assert result.cash_out == 16_500.0
    assert result.net_cash_flow == 16_500.0
    assert result.net_cash_flow == (
        result.operating.net + result.investing.net + result.financing.net
    )


def test_interest_paid_affects_financing_only():
    base = calculate_monthly_dairy_cash_flow(_cash_model(interest_paid=500))
    high = calculate_monthly_dairy_cash_flow(_cash_model(interest_paid=1_500))
    assert high.financing.outflows.lines["interest_paid"] == 1_500.0
    assert high.financing.outflows.total == base.financing.outflows.total + 1_000.0
    assert high.financing.net == base.financing.net - 1_000.0
    assert high.cash_out == base.cash_out + 1_000.0
    assert high.net_cash_flow == base.net_cash_flow - 1_000.0
    assert high.operating.model_dump() == base.operating.model_dump()
    assert high.investing.model_dump() == base.investing.model_dump()
    assert "interest_paid" not in high.operating.outflows.lines
    assert "interest_paid" not in high.investing.outflows.lines


def test_loan_principal_is_financing_and_does_not_touch_pnl():
    cash = calculate_monthly_dairy_cash_flow(
        _cash_model(loan_principal_repayments=9_999)
    )
    assert cash.financing.outflows.lines["loan_principal_repayments"] == 9_999.0
    assert "loan_principal_repayments" not in cash.operating.outflows.lines

    annual = calculate_annual_pnl(
        FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    )
    assert annual.revenue.total == 240_000.0
    assert annual.costs.total == 163_000.0
    assert annual.profit.net == 77_000.0
    assert annual.profit.margin_pct == 32.08
    assert annual.finance.loan_repayments == 12_000.0

    monthly_pnl = calculate_monthly_dairy_statement(
        MonthlyDairyStatementModel(
            period=MonthlyPeriodIdentity(year=2026, month=3),
            inputs=MonthlyDairyFinancialInput.model_validate(
                {
                    "milk_litres": 40_000,
                    "milk_price": 0.40,
                    "biss": 2_000,
                    "acres": 500,
                    "cattle_sales": 1_000,
                    "feed": 5_000,
                    "fertiliser": 1_000,
                    "loan_repayments": 1_500,
                }
            ),
        )
    )
    assert monthly_pnl.revenue.total == 19_500.0
    assert monthly_pnl.costs.total == 6_000.0
    assert monthly_pnl.profit.net == 13_500.0
    assert monthly_pnl.profit.margin == 0.6923
    assert monthly_pnl.profit.margin_pct == 69.23
    assert monthly_pnl.finance.loan_repayments == 1_500.0


def test_capex_is_investing_not_operating():
    result = calculate_monthly_dairy_cash_flow(
        _cash_model(machinery_equipment_payments=6_000)
    )
    assert result.investing.outflows.lines["machinery_equipment_payments"] == 6_000.0
    assert "machinery_equipment_payments" not in result.operating.outflows.lines


def test_zero_month_publishes_all_catalogue_keys():
    result = calculate_monthly_dairy_cash_flow(
        MonthlyDairyCashFlowModel(
            period=MonthlyPeriodIdentity(year=2026, month=1),
            inputs=MonthlyDairyCashFlowInput.model_validate({}),
        )
    )
    assert result.cash_in == 0.0
    assert result.cash_out == 0.0
    assert result.net_cash_flow == 0.0
    assert set(result.operating.inflows.lines) == set(OPERATING_CASH_INFLOW_CATEGORIES)
    assert set(result.operating.outflows.lines) == set(OPERATING_CASH_OUTFLOW_CATEGORIES)
    assert set(result.investing.outflows.lines) == set(INVESTING_CASH_OUTFLOW_CATEGORIES)
    assert set(result.financing.outflows.lines) == set(FINANCING_CASH_OUTFLOW_CATEGORIES)
    assert all(v == 0.0 for v in result.operating.inflows.lines.values())


def test_calculation_does_not_mutate_model_and_stamps_period():
    model = _cash_model()
    before = model.model_dump()
    result = calculate_monthly_dairy_cash_flow(model)
    assert model.model_dump() == before
    assert result.period.year == 2026
    assert result.period.month == 3


def test_dairy_cash_flow_does_not_import_pnl_composers():
    text = DAIRY_CASH.read_text(encoding="utf-8")
    for needle in (
        "monthly_pl_summary",
        "pl_summary",
        "milk_revenue",
        "total_costs",
        "farm_functions.dairy.statement",
        "farm_functions.dairy.monthly_statement",
        "from farm_functions.dairy.statement",
        "from farm_functions.dairy.monthly_statement",
        "import farm_functions.dairy.statement",
        "import farm_functions.dairy.monthly_statement",
    ):
        assert needle not in text


def test_monthly_cash_flow_accepts_kwargs_directly():
    payload = monthly_cash_flow(**REFERENCE_INPUTS)
    assert payload["cash_in"] == 33_000.0
    assert payload["net_cash_flow"] == 16_500.0
    assert "period" not in payload


def test_cash_and_pnl_share_category_ids():
    """ADR-0023: one invoice category ID feeds both statements."""
    pnl_costs = set(TotalCostsInput.model_fields)
    pnl_income = set(SchemeRevenueInput.model_fields) | set(OtherRevenueInput.model_fields)
    assert set(OPERATING_CASH_OUTFLOW_CATEGORIES) == pnl_costs
    assert set(OPERATING_CASH_INFLOW_CATEGORIES) == pnl_income | {"milk"}
    assert set(CASH_FLOW_LINES) == set(MonthlyDairyCashFlowInput.model_fields)


def test_old_cash_suffix_names_are_rejected():
    import pytest
    from pydantic import ValidationError

    for old in ("feed_payments", "milk_receipts", "scheme_receipts"):
        with pytest.raises(ValidationError):
            MonthlyDairyCashFlowInput.model_validate({old: 1})
