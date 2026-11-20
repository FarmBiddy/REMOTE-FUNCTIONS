"""cf.reconcile (ADR-0055 §6): from accounts profit to the months' operating cash.

Hand check, Jan–Mar 2026 (sample_data/examples/cf.reconcile.json):
  milk 80,000 L × 0.45 = 36,000; costs feed 23,000 + fertiliser 4,500 + labour 7,500
  Operating Surplus 1,000; herd +6,000, stock −2,000 → accounts operating profit 5,000
  bridge: herd −6,000, stock +2,000, milk owed 3,150 → 22,500 (−19,350),
          merchant credit 38,000 → 48,000 (+10,000) → −13,350
  expected operating cash 5,000 − 13,350 = −8,350
  cash months: in 3,150 + 2,700 + 10,800 = 16,650, out 13,000 + 4,500 + 7,500 = 25,000 → −8,350
"""

import json
from pathlib import Path

from farm_functions.runner import run_function

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / "sample_data/examples/cf.reconcile.json").read_text())


def _run(**overrides):
    return run_function("cf.reconcile", {**EXAMPLE, **overrides})


def test_spring_quarter_reconciles():
    body = _run()["result"]
    assert (body["operating_surplus"], body["accounts_operating_profit"]) == (1_000, 5_000)
    assert body["bridge"] == {
        "herd_value_change": -6_000, "stock_value_change": 2_000, "milk_debtors": -19_350,
        "other_debtors": 0, "merchant_credit": 10_000, "other_creditors": 0,
    }
    assert (body["expected_operating_cash"], body["actual_operating_cash"]) == (-8_350, -8_350)
    assert (body["unexplained"], body["unexplained_pct_of_revenue"]) == (0, 0)


def test_unrecorded_merchant_credit_shows_as_unexplained():
    """Leave the merchant account out: the 10,000 it funded is unexplained (27.78% of revenue)."""
    body = _run(merchant_credit_opening=0, merchant_credit_closing=0)["result"]
    assert (body["unexplained"], body["unexplained_pct_of_revenue"]) == (10_000, 27.78)


def test_months_must_match():
    result = _run(cf_months=EXAMPLE["cf_months"][:2])
    assert result["errors"][0]["details"]["reason"] == "periods_misaligned"
