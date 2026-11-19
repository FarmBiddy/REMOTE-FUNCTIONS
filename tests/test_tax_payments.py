"""tax.payments (ADR-0055 §2b): preliminary tax and the pay date.

Hand check, tax year 2026, a good year (2025) followed by a weaker one:
  this year 21,400, last year 36,200 (30,000 paid as preliminary), year before 18,900
  options: 90% × 21,400 = 19,260; 100% × 36,200 = 36,200; 105% × 18,900 = 19,845 (DD only)
  lowest safe without direct debit: 19,260 (90% of this year)
  last year's balance 36,200 − 30,000 = 6,200
  due on the pay date (31 Oct, ROS 18 Nov 2026): 6,200 + 19,260 = 25,460
  left for next year's return: 21,400 − 19,260 = 2,140
  by direct debit from March on 105%: 19,845 / 10 = 1,984.50 a month; only 6,200 due that day
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

BASE = {
    "tax_year": 2026,
    "current_year_tax": 21_400,
    "preceding_year_tax": 36_200,
    "preceding_year_preliminary_paid": 30_000,
    "pre_preceding_year_tax": 18_900,
    "preliminary_basis": "current_90",
}
DD = {**BASE, "preliminary_basis": "pre_preceding_105_dd", "direct_debit": True, "direct_debit_start_month": 3}


def _run(**overrides):
    return run_function("tax.payments", {**BASE, **overrides})


def _ok(**overrides):
    result = _run(**overrides)
    assert result["status"] == "ok", result
    return result["result"]


def _reason(**overrides):
    result = _run(**overrides)
    assert result["status"] == "error", result
    return result["errors"][0]["details"]["reason"]


def test_good_year_then_weaker_year():
    body = _ok()
    assert [(o["basis"], o["amount"], o["available"]) for o in body["options"]] == [
        ("current_90", 19_260, True), ("prior_100", 36_200, True), ("pre_preceding_105_dd", 19_845, False),
    ]
    assert body["lowest_safe"] == {"basis": "current_90", "amount": 19_260}
    assert body["preliminary"] == {"basis": "current_90", "amount": 19_260}
    assert body["preceding_year"] == {
        "tax_year": 2025, "liability": 36_200, "preliminary_paid": 30_000, "balance_due": 6_200, "overpaid": 0,
    }
    assert body["pay_date"] == {"statutory": "2026-10-31", "ros": "2026-11-18", "ros_source": "Revenue eBrief 034/26"}
    assert body["due_on_pay_date"] == 25_460
    assert body["balance_next_year"] == 2_140
    assert body["direct_debit_instalments"] is None
    assert [r["legal_ref"] for r in body["rules_applied"]][0] == "TCA s.959AO(3)(b)(i)"


def test_platform_choice_is_kept_even_when_not_the_lowest():
    body = _ok(preliminary_basis="prior_100")
    assert body["preliminary"]["amount"] == 36_200 and body["lowest_safe"]["basis"] == "current_90"
    assert body["due_on_pay_date"] == 42_400 and body["balance_next_year"] == -14_800


def test_direct_debit_spreads_the_preliminary():
    body = run_function("tax.payments", DD)["result"]
    assert body["options"][2]["available"] is True
    assert [i["month"] for i in body["direct_debit_instalments"]] == list(range(3, 13))
    assert {(i["day"], i["amount"]) for i in body["direct_debit_instalments"]} == {(9, 1_984.5)}
    assert body["due_on_pay_date"] == 6_200


def test_instalment_cents_go_in_the_last_month():
    body = _ok(current_year_tax=1_000, preliminary_basis="prior_100", preceding_year_tax=1_000,
               direct_debit=True, direct_debit_start_month=10)
    assert [i["amount"] for i in body["direct_debit_instalments"]] == [333.33, 333.33, 333.34]


def test_overpayment_is_shown_not_netted():
    body = _ok(preceding_year_preliminary_paid=40_000)
    assert (body["preceding_year"]["balance_due"], body["preceding_year"]["overpaid"]) == (0, 3_800)
    assert body["due_on_pay_date"] == 19_260


def test_years_without_an_announced_ros_date():
    body = _ok(tax_year=2027)
    assert body["pay_date"] == {"statutory": "2027-10-31", "ros": None, "ros_source": None}


def test_missing_and_invalid_inputs():
    no_basis = run_function("tax.payments", {k: v for k, v in BASE.items() if k != "preliminary_basis"})
    assert no_basis["status"] == "needs_input" and no_basis["missing"][0]["field"] == "preliminary_basis"
    no_month = _run(direct_debit=True)
    assert [m["path"] for m in no_month["missing"]] == ["direct_debit_start_month"]
    no_base = run_function("tax.payments", {k: v for k, v in DD.items() if k != "pre_preceding_year_tax"})
    assert [m["path"] for m in no_base["missing"]] == ["pre_preceding_year_tax"]
    assert _reason(preliminary_basis="pre_preceding_105_dd") == "needs_direct_debit"
    assert _reason(direct_debit_start_month=4) == "needs_direct_debit"
    assert run_function("tax.payments", {**DD, "pre_preceding_year_tax": 0})["errors"][0]["details"]["reason"] == "basis_not_available"
    assert _reason(tax_year=2028) == "rule_not_available"


def test_http_matches_runner():
    assert client.post("/v1/functions/tax.payments/run", json=BASE).json() == _run()
