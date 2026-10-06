"""decision.investment (ADR-0046): NPV, IRR, paybacks.

Reference: €100,000 parlour saving €12,000 a year for 15 years at a 5% discount rate.
  Annuity factor (15 years, 5%) = 10.3797 → PV of benefits 124,555.90 → NPV 24,555.90
  IRR 8.44% (rate where the factor equals 100,000 / 12,000 = 8.333)
  Simple payback 8.33 years; discounted payback 11.05 years; PI 1.2456
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.core.investment import discounted_payback, irr, npv
from farm_functions.runner import run_function

client = TestClient(app)

PARLOUR = {"amount": 100_000, "discount_rate": 0.05, "annual_benefit": 12_000, "life_years": 15}


def _appraise(**overrides):
    return run_function("decision.investment", {**PARLOUR, **overrides})


def test_reference_parlour():
    body = _appraise()["result"]
    assert body["npv"] == 24_555.9
    assert body["irr_pct"] == 8.44
    assert (body["simple_payback_years"], body["discounted_payback_years"]) == (8.33, 11.05)
    assert body["profitability_index"] == 1.2456
    assert body["worthwhile"] is True
    assert body["years"][0] == {
        "year": 1, "cash_flow": 12_000, "discount_factor": 0.952381,
        "present_value": 11_428.57, "cumulative_present_value": -88_571.43,
    }
    assert body["years"][-1]["cumulative_present_value"] == body["npv"]


def test_npv_is_zero_at_irr():
    flows = [-100_000] + [12_000] * 15
    assert abs(npv(irr(flows), flows)) < 1e-6


def test_explicit_cash_flows_and_residual_value():
    """Benefits ramp up; tractor sold for 20,000 at the end."""
    body = _appraise(
        annual_benefit=None, life_years=None,
        cash_flows=[5_000, 10_000, 15_000, 15_000, 15_000], residual_value=20_000,
    )["result"]
    assert body["life_years"] == 5
    assert body["years"][-1]["cash_flow"] == 35_000
    flows = [-100_000, 5_000, 10_000, 15_000, 15_000, 35_000]
    assert body["npv"] == round(npv(0.05, flows), 2)


def test_higher_discount_rate_can_flip_the_decision():
    assert _appraise(discount_rate=0.10)["result"]["worthwhile"] is False


def test_never_pays_back():
    body = _appraise(annual_benefit=1_000)["result"]
    assert body["discounted_payback_years"] is None and body["simple_payback_years"] is None
    assert discounted_payback(0.05, [-100, 10]) is None


def test_benefit_form_is_required_once():
    assert _appraise(annual_benefit=None, life_years=None)["error"]["details"]["reason"] == "benefit_form"
    both = _appraise(cash_flows=[1_000])
    assert both["error"]["details"]["reason"] == "benefit_form"
    assert _appraise(life_years=41)["error"]["details"] == {"minimum": 1, "maximum": 40}


def test_http_matches_runner():
    body = client.post("/v1/functions/decision.investment/run", json=PARLOUR).json()
    assert body == run_function("decision.investment", PARLOUR)
