"""P3.1 Cash Flow Core arithmetic and Domain contracts (ADR-0022).

No monthly cash calculation yet — that is P3.2.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from farm_functions.core.cash import (
    CashActivity,
    CashDirection,
    cash_section_net,
    net_cash_flow,
    sum_cash_amounts,
)
from farm_functions.domain import (
    MonthlyDairyCashFlowModel,
    MonthlyDairyCashFlowResult,
    MonthlyPeriodIdentity,
)
from farm_functions.schemas import MonthlyDairyCashFlowInput

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "farm_functions" / "core"


def test_cash_section_net_and_net_cash_flow():
    assert cash_section_net(10_000, 4_000) == 6_000
    assert net_cash_flow(50_000, 40_000) == 10_000
    assert net_cash_flow(0, 100) == -100
    assert sum_cash_amounts(1, 2, 3) == 6


def test_core_cash_module_has_no_interest_policy():
    """D-CF1: Core must not hard-code interest classification."""
    text = (CORE / "cash.py").read_text(encoding="utf-8")
    assert "interest_paid" not in text
    assert "loan_principal" not in text
    assert "milk" not in text
    # No policy mapping tables in Core.
    assert "financing" not in text or "CashActivity" in text


def test_core_cash_has_no_pnl_coupling():
    text = (CORE / "cash.py").read_text(encoding="utf-8")
    for needle in ("pl_summary", "FinancialInput", "loan_repayments", "Operating Surplus"):
        assert needle not in text


def test_cash_direction_and_activity_literals():
    assert "in" in CashDirection.__args__
    assert "out" in CashDirection.__args__
    assert set(CashActivity.__args__) == {"operating", "investing", "financing"}


def test_monthly_cash_flow_input_defaults_and_rejects_negatives():
    parsed = MonthlyDairyCashFlowInput.model_validate({})
    assert parsed.milk == 0
    assert parsed.loan_proceeds == 0
    assert parsed.interest_paid == 0
    assert parsed.machinery_equipment_payments == 0
    with pytest.raises(ValidationError):
        MonthlyDairyCashFlowInput.model_validate({"milk": -1})


def test_monthly_cash_flow_input_rejects_pnl_fields_and_calendar():
    with pytest.raises(ValidationError):
        MonthlyDairyCashFlowInput.model_validate({"loan_repayments": 100})
    with pytest.raises(ValidationError):
        MonthlyDairyCashFlowInput.model_validate({"milking_cows": 100})
    with pytest.raises(ValidationError):
        MonthlyDairyCashFlowInput.model_validate({"year": 2026, "month": 3})
    with pytest.raises(ValidationError):
        MonthlyDairyCashFlowInput.model_validate({"household_drawings": 500})


def test_interest_paid_is_on_financing_catalogue_not_core():
    """Phase 1 Dairy grouping places interest under financing outflows (policy)."""
    parsed = MonthlyDairyCashFlowInput.model_validate({"interest_paid": 250})
    assert parsed.interest_paid == 250
    dump = parsed.model_dump()
    assert "interest_paid" in dump
    assert dump["interest_paid"] == 250


def test_monthly_cash_flow_model_separates_identity():
    model = MonthlyDairyCashFlowModel(
        period=MonthlyPeriodIdentity(year=2026, month=1),
        inputs=MonthlyDairyCashFlowInput.model_validate(
            {
                "milk": 16_000,
                "feed": 5_000,
                "loan_proceeds": 50_000,
                "machinery_equipment_payments": 40_000,
                "loan_principal_repayments": 1_000,
                "interest_paid": 200,
            }
        ),
    )
    assert model.period.model_dump() == {"kind": "month", "year": 2026, "month": 1}
    assert "year" not in model.inputs.model_dump()
    assert model.inputs.loan_proceeds == 50_000


def test_monthly_cash_flow_result_shape_accepts_hand_payload():
    """Contract shape only — P3.2 will produce this from composition."""
    result = MonthlyDairyCashFlowResult.model_validate(
        {
            "currency": "EUR",
            "period": {"kind": "month", "year": 2026, "month": 1},
            "operating": {
                "inflows": {"lines": {"milk": 16_000}, "total": 16_000},
                "outflows": {"lines": {"feed": 5_000}, "total": 5_000},
                "net": 11_000,
            },
            "investing": {
                "inflows": {"lines": {}, "total": 0},
                "outflows": {
                    "lines": {"machinery_equipment_payments": 40_000},
                    "total": 40_000,
                },
                "net": -40_000,
            },
            "financing": {
                "inflows": {"lines": {"loan_proceeds": 50_000}, "total": 50_000},
                "outflows": {
                    "lines": {
                        "loan_principal_repayments": 1_000,
                        "interest_paid": 200,
                    },
                    "total": 1_200,
                },
                "net": 48_800,
            },
            "cash_in": 66_000,
            "cash_out": 46_200,
            "net_cash_flow": 19_800,
            "opening_cash": None,
            "closing_cash": None,
        }
    )
    assert result.net_cash_flow == 19_800
    assert result.financing.outflows.lines["interest_paid"] == 200
    assert result.opening_cash is None and result.closing_cash is None


def test_monthly_cash_calculation_entrypoint_exists():
    import farm_functions.domain as domain

    assert hasattr(domain, "calculate_monthly_dairy_cash_flow")
