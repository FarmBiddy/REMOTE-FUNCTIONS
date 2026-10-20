"""Teagasc NFS alignment: casual labour as a direct cost and the NFS view in kpi.summary.

Hand check, 12 months of 40,000 L × 0.40 = 16,000 milk, BISS 12,000 once,
feed 5,000, casual labour 500, regular labour 2,000 a month:
  revenue 204,000 (milk 192,000 + BISS 12,000); costs 90,000
  direct (variable) = feed 60,000 + casual 6,000 = 66,000; operating fixed 24,000
  depreciation 12,000, interest 4,000; herd +10,000, feed stock −3,000 → +7,000
  gross output 211,000 − direct 66,000 − overheads (24,000 + 12,000 + 4,000) = FFI 105,000
  per litre (480,000 L): dairy output (211,000 − 12,000 BISS) 41.46c, direct 13.75c,
  fixed 7.50c, total 21.25c, net margin 20.21c
"""

from farm_functions.dairy.costs import FIXED_COST_CATEGORIES, VARIABLE_COST_CATEGORIES
from farm_functions.runner import run_function

MONTHS = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "biss": 12_000 if m == 1 else 0,
     "feed": 5_000, "casual_labour": 500, "labour": 2_000}
    for m in range(1, 13)
]
VALUES = {"livestock_opening_value": 300_000, "livestock_closing_value": 310_000,
          "stock_opening_value": 8_000, "stock_closing_value": 5_000}


def _kpis(**extra):
    result = run_function("kpi.summary", {"months": MONTHS, "milking_cows": 100, **extra})
    assert result["status"] == "ok", result
    return result["result"]


def test_casual_labour_is_variable_regular_labour_is_fixed():
    assert "casual_labour" in VARIABLE_COST_CATEGORIES and "labour" in FIXED_COST_CATEGORIES
    per_litre = _kpis()["per_litre_c"]
    assert (per_litre["variable_costs"], per_litre["fixed_costs"]) == (13.75, 5)
    assert per_litre["cost_lines"]["casual_labour"] == 1.25


def test_teagasc_view():
    body = _kpis(depreciation=12_000, interest=4_000, **VALUES)["teagasc"]
    assert (body["gross_output"], body["direct_costs"], body["overhead_costs"]) == (211_000, 66_000, 40_000)
    assert body["family_farm_income"] == 105_000
    assert body["per_litre_c"] == {"gross_output": 41.46, "direct_costs": 13.75, "fixed_costs": 7.5,
                                   "total_costs": 21.25, "net_margin": 20.21}


def test_family_farm_income_equals_pl_net_profit():
    """Same inputs, same answer: FFI is pl.net's net profit before tax on NFS terms."""
    net = run_function("pl.net", {"months": MONTHS, "depreciation": 12_000, "interest": 4_000, **VALUES})["result"]
    assert _kpis(depreciation=12_000, interest=4_000, **VALUES)["teagasc"]["family_farm_income"] == net["net_profit_before_tax"]


def test_teagasc_view_needs_depreciation():
    assert _kpis()["teagasc"] is None
