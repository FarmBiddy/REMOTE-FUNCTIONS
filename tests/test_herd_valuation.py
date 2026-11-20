"""herd.valuation (ADR-0055 §7): the herd at a valuation date, market and Revenue practice.

Hand check (sample_data/examples/herd.valuation.json), 31 Dec 2026:
  110 cows    market 2,400, held 1,900 → 264,000 market, 209,000 practice (held value)
   28 heifers market 2,100 → 58,800, × 60% = 35,280
   30 weanlings     950    → 28,500, × 60% = 17,100
   12 calves        120    →  1,440, × 60% =    864
    1 bull     market 2,200, held 2,800 → 2,200 both (written down to market)
  total 181 head: market 354,940, Revenue practice 264,444
"""

import json
from pathlib import Path

from farm_functions.runner import run_function

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / "sample_data/examples/herd.valuation.json").read_text())


def _run(**overrides):
    return run_function("herd.valuation", {**EXAMPLE, **overrides})


def test_market_and_revenue_practice_side_by_side():
    body = _run()["result"]
    assert [(g["market_value"], g["revenue_practice_value"], g["revenue_practice_basis"]) for g in body["groups"]] == [
        (264_000, 209_000, "held_value"),
        (58_800, 35_280, "deemed_cost_pct"),
        (28_500, 17_100, "deemed_cost_pct"),
        (1_440, 864, "deemed_cost_pct"),
        (2_200, 2_200, "written_down_to_market"),
    ]
    assert body["total"] == {"head": 181, "market_value": 354_940, "revenue_practice_value": 264_444}
    rule = body["rules_applied"][0]
    assert (rule["rule_id"], rule["value"], rule["status"]) == ("livestock_deemed_cost_cattle_pct", 60, "practice")


def test_young_sheep_at_75_percent():
    body = _run(groups=[{"category": "lambs", "head": 100, "unit_market_value": 150}])["result"]
    assert body["total"]["revenue_practice_value"] == 11_250


def test_held_value_is_asked_for_mature_stock_only():
    cows = {"category": "dairy_cows", "head": 1, "unit_market_value": 2_000}
    missing = _run(groups=[cows])
    assert missing["status"] == "needs_input" and [m["path"] for m in missing["missing"]] == ["groups[0].unit_held_value"]
    calves = {"category": "calves", "head": 1, "unit_market_value": 300, "unit_held_value": 200}
    assert _run(groups=[calves])["errors"][0]["details"]["reason"] == "held_value_not_used"
    assert _run(year=2028)["errors"][0]["details"]["reason"] == "rule_not_available"


def test_total_feeds_stock_relief():
    """The Revenue-practice total is the closing livestock value tax.stock_relief takes."""
    closing = _run()["result"]["total"]["revenue_practice_value"]
    relief = run_function("tax.stock_relief", {
        "business_type": "sole_trader", "period_end_year": 2026, "trading_profit": 80_000,
        "livestock_opening_value": 250_000, "livestock_closing_value": closing,
    })["result"]
    assert (relief["stock_increase"], relief["relief"]) == (14_444, 3_611)
