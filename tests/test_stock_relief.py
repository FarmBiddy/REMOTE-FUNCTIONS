"""tax.stock_relief (ADR-0053): Irish farm stock relief.

Hand check: trading stock 308,000 (300,000 herd + 8,000 feed) → 340,000
(330,000 + 10,000) = increase 32,000.
  general 25%                 →  8,000 relief on 50,000 profit → 42,000
  registered partnership 50%  → 16,000
  young trained farmer 100%   → 32,000; on 20,000 profit only 20,000 (no loss)
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

BASE = {
    "business_type": "sole_trader",
    "period_end_year": 2026,
    "trading_profit": 50_000,
    "livestock_opening_value": 300_000,
    "livestock_closing_value": 330_000,
    "stock_opening_value": 8_000,
    "stock_closing_value": 10_000,
}


def _run(**overrides):
    return run_function("tax.stock_relief", {**BASE, **overrides})


def _ok(**overrides):
    result = _run(**overrides)
    assert result["status"] == "ok", result
    return result["result"]


def _reason(**overrides):
    result = _run(**overrides)
    assert result["status"] == "error"
    return result["errors"][0]["details"]["reason"]


def test_general_relief():
    body = _ok()
    assert (body["stock_increase"], body["regime"], body["rate_pct"]) == (32_000, "general", 25.0)
    assert (body["relief"], body["profit_after_relief"]) == (8_000, 42_000)
    assert body["restricted_by_profit"] is False and body["losses_forward_restricted"] is True
    assert body["caps_not_applied"] == []
    assert body["rules_applied"][0]["legal_ref"] == "TCA s.666"


def test_registered_partnership_partner_gets_half():
    body = _ok(business_type="partnership", registered_partnership=True)
    assert (body["regime"], body["relief"]) == ("registered_partnership", 16_000)
    assert body["caps_not_applied"] == ["stock_relief_rfp_de_minimis"]


def test_young_trained_farmer_window_is_four_tax_years():
    assert _ok(young_trained_farmer_first_year=2023)["relief"] == 32_000  # 2023–2026
    assert _ok(young_trained_farmer_first_year=2022)["regime"] == "general"  # window ended 2025
    after = _ok(business_type="partnership", registered_partnership=True, young_trained_farmer_first_year=2022)
    assert after["regime"] == "registered_partnership"


def test_relief_never_creates_or_increases_a_loss():
    body = _ok(young_trained_farmer_first_year=2026, trading_profit=20_000)
    assert (body["relief_before_profit_limit"], body["relief"], body["profit_after_relief"]) == (32_000, 20_000, 0)
    assert body["restricted_by_profit"] is True
    loss = _ok(trading_profit=-5_000)
    assert (loss["relief"], loss["profit_after_relief"], loss["losses_forward_restricted"]) == (0, -5_000, False)


def test_falling_stock_gives_no_relief():
    assert _ok(livestock_closing_value=250_000)["relief"] == 0


def test_companies_get_general_relief_only():
    assert _ok(business_type="company")["regime"] == "general"
    assert _reason(business_type="company", young_trained_farmer_first_year=2026) == "regime_not_available"
    assert _reason(registered_partnership=True) == "regime_not_available"  # sole trader


def test_period_outside_the_rules_is_an_error_not_a_guess():
    assert _reason(period_end_year=2028) == "rule_not_available"
    assert _reason(young_trained_farmer_first_year=2027) == "period_reversed"


def test_http_matches_runner():
    assert client.post("/v1/functions/tax.stock_relief/run", json=BASE).json() == _run()
