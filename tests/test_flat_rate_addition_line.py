"""flat_rate_addition P&L and cash line (ADR-0055 §3).

The flat-rate VAT addition an unregistered farmer receives on milk and cattle
sales is farm income in the accounts. The Platform takes the amount from
vat.flat_rate (Irish rules stay in the ie layer) and sends it as a monthly
line; it is published inside revenue.other.

Hand check, 2026 (4.5%): 25,000 L × 0.40 = 10,000 milk → addition 450.
  milk price −4c → 9,000 milk → addition follows the sales: 405
  surplus change −1,000 − 45 = −1,045
"""

import pytest

from farm_functions.runner import run_function

MONTH = {"year": 2026, "month": 5, "milk_litres": 25_000, "milk_price": 0.40, "feed": 4_000}


def _ok(name, body):
    result = run_function(name, body)
    assert result["status"] == "ok", result
    return result["result"]


def test_pl_line_is_in_other_revenue():
    vat = _ok("vat.flat_rate", {"months": [MONTH]})
    fra = vat["months"][0]["addition"]
    assert fra == 450
    body = _ok("pl.monthly", {**MONTH, "flat_rate_addition": fra})
    assert (body["revenue"]["milk"], body["revenue"]["other"], body["revenue"]["total"]) == (10_000, 450, 10_450)
    assert body["profit"]["net"] == 6_450


def test_cash_line_is_an_operating_inflow():
    body = _ok("cf.monthly", {"year": 2026, "month": 5, "milk": 10_000, "flat_rate_addition": 450})
    assert body["operating"]["inflows"]["lines"]["flat_rate_addition"] == 450
    assert body["net_cash_flow"] == 10_450


def test_taxable_profit_counts_it_once():
    """vat.flat_rate → pl.months line → pl.net → tax bridge: no separate addition."""
    months = [{**MONTH, "month": m} for m in range(1, 13)]
    vat = _ok("vat.flat_rate", {"months": months})
    with_fra = [{**m, "flat_rate_addition": v["addition"]} for m, v in zip(months, vat["months"])]
    net = _ok("pl.net", {"months": with_fra})
    assert net["revenue"] == pytest.approx(12 * 10_450, abs=0.01)
    bridge = _ok("tax.capital_allowances", {
        "tax_year": 2026, "accounting_profit": net["net_profit_before_tax"],
        "assets": [{"cost": 8_000, "year": 2026, "month": 2, "life_months": 96}],
    })["profit_bridge"]
    assert bridge["taxable_profit"] == pytest.approx(12 * 6_450 - 1_000, abs=0.01)


def test_scenarios_move_it_with_sales():
    pl = [{**MONTH, "flat_rate_addition": 450}]
    cf = [{"year": 2026, "month": 5, "milk": 10_000, "flat_rate_addition": 450, "feed": 4_000}]
    body = _ok("risk.sensitivity", {"pl_months": pl, "cf_months": cf, "opening_cash": 0,
                                    "scenarios": [{"name": "price down", "milk_price_c": -4}]})
    base, down = body["scenarios"]
    assert base["operating_surplus"] - down["operating_surplus"] == pytest.approx(1_045, abs=0.01)
    assert base["closing_cash"] - down["closing_cash"] == pytest.approx(1_045, abs=0.01)


def test_tornado_does_not_treat_it_as_a_driver():
    pl = [{**MONTH, "flat_rate_addition": 450}]
    cf = [{"year": 2026, "month": 5, "milk": 10_000, "flat_rate_addition": 450, "feed": 4_000}]
    body = _ok("risk.tornado", {"pl_months": pl, "cf_months": cf, "opening_cash": 0})
    assert "flat_rate_addition" not in {d["driver"] for d in body["drivers"]}


def test_projection_carries_it_with_sales_or_rejects_it_with_a_tax_profile():
    base = [{**MONTH, "month": m, "flat_rate_addition": 450} for m in range(1, 13)]
    years = _ok("plan.projection", {"base_pl_months": base, "opening_cash": 0, "milking_cows": 100,
                                    "years": 2, "assumptions": {"milk_price": [0.40, 0.44]}})["years"]
    # 10% higher milk price → 10% more sales → addition 5,400 → 5,940.
    assert [y["pl"]["revenue"]["other"] for y in years] == [5_400, 5_940]
    clash = run_function("plan.projection", {
        "base_pl_months": base, "opening_cash": 0, "milking_cows": 100,
        "tax_profile": {"business_type": "company", "vat_registered": False},
    })
    assert clash["errors"][0]["details"]["reason"] == "fra_conflict"
