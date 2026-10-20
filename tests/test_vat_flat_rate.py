"""vat.flat_rate (ADR-0053): Irish flat-rate farmer VAT addition.

Hand check across the 2025 → 2026 rate change:
  Dec 2025: 40,000 L × 0.50 = 20,000 milk + 2,000 cattle = 22,000 × 5.1% = 1,122
  Jan 2026: 40,000 L × 0.50 = 20,000 milk                = 20,000 × 4.5% =   900
"""

from datetime import date

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.ie import FLAT_RATE_ADDITION, rule_at
from farm_functions.runner import run_function

client = TestClient(app)

MONTHS = [
    {"year": 2026, "month": 1, "milk_litres": 40_000, "milk_price": 0.50, "biss": 9_000, "feed": 5_000},
    {"year": 2025, "month": 12, "milk_litres": 40_000, "milk_price": 0.50, "cattle_sales": 2_000},
]


def _run(**body):
    return run_function("vat.flat_rate", {"months": MONTHS, **body})


def test_rate_follows_the_month_and_only_agricultural_sales_count():
    body = _run()["result"]
    assert [(m["period"]["month"], m["rate_pct"], m["addition"]) for m in body["months"]] == [
        (12, 5.1, 1_122), (1, 4.5, 900)
    ]
    assert body["total"] == {"milk": 40_000, "cattle_sales": 2_000, "base": 42_000, "addition": 2_022}
    assert [(r["value"], r["legal_ref"], r["status"]) for r in body["rules_applied"]] == [
        (5.1, "FA2024 s.83", "enacted"), (4.5, "FA2025 s.73", "enacted")
    ]


def test_registered_farmers_get_no_addition():
    body = _run(vat_registered=True)["result"]
    assert body["total"]["addition"] == 0 and body["total"]["base"] == 42_000
    assert body["rules_applied"] == [] and body["months"][0]["rate_pct"] is None


def test_announced_rate_is_flagged():
    month = {"year": 2027, "month": 1, "milk_litres": 1_000, "milk_price": 0.50}
    body = run_function("vat.flat_rate", {"months": [month]})["result"]
    assert body["total"]["addition"] == 24  # 500 × 4.8%
    assert body["rules_applied"][0]["status"] == "announced"


def test_month_without_a_rule_is_an_error_not_a_guess():
    month = {"year": 2014, "month": 12, "milk_litres": 1_000, "milk_price": 0.50}
    result = run_function("vat.flat_rate", {"months": [month]})
    assert result["status"] == "error"
    assert result["errors"][0]["details"]["reason"] == "rule_not_available"
    assert run_function("vat.flat_rate", {"months": [month], "vat_registered": True})["status"] == "ok"


def test_rate_table_has_no_gaps_or_overlaps():
    rules = sorted(FLAT_RATE_ADDITION, key=lambda r: r.start)
    for prev, nxt in zip(rules, rules[1:]):
        assert prev.end is not None and (nxt.start - prev.end).days == 1
    assert rules[-1].end is None
    assert rule_at(FLAT_RATE_ADDITION, date(2014, 12, 31)) is None


def test_http_matches_runner():
    body = client.post("/v1/functions/vat.flat_rate/run", json={"months": MONTHS}).json()
    assert body == _run()
