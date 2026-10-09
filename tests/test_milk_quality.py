"""milk.quality (ADR-0052): weighted figures, EU compliance, benchmarks, value.

Reference quarter (100 cows, 40 ha):
  Jan 10,000 L  fat 4.0  protein 3.4  SCC 300  TBC 20
  Feb 30,000 L  fat 4.2  protein 3.5  SCC 150  TBC 10
  Mar 60,000 L  fat 4.0  protein 3.4  SCC 450  TBC 8
  Weighted fat (40 + 126 + 240) / 100 = 4.06% (simple mean would be 4.07%)
  Weighted SCC (3,000 + 4,500 + 27,000) / 100 = 345
  March rolling SCC = ∛(300 × 150 × 450) = 272.57 → no EU breach despite 450 in the month
  Solids 100,000 × 1.03 × 7.49% = 7,714.7 kg → 77.15 kg/cow, 192.87 kg/ha
Pricing €6/kg fat, €8/kg protein, 3c/L volume charge; SCC bands ≤100 +0.5c, ≤400 0c, above −1c;
TBC bands ≤10 +0.25c, above 0c:
  fat 4,181.8 kg × 6 = 25,090.80; protein 3,532.9 kg × 8 = 28,263.20; volume −3,000
  SCC: March 450 → −1c × 60,000 = −600; TBC: Feb + Mar → 0.25c × 90,000 = +225
  To top 10% (fat 4.6, protein 3.7): 556.2 kg × 6 + 278.1 kg × 8 = 5,562
  Best bands every month: SCC 50 + 150 + 900, TBC 25 = 1,125
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.core.statistics import geometric_mean, weighted_mean
from farm_functions.runner import run_function

client = TestClient(app)


def _month(month, litres, fat, protein, scc, tbc, year=2026):
    return {"year": year, "month": month, "milk_litres": litres, "fat_pct": fat,
            "protein_pct": protein, "scc_k": scc, "tbc_k": tbc}


QUARTER = [_month(3, 60_000, 4.0, 3.4, 450, 8), _month(1, 10_000, 4.0, 3.4, 300, 20), _month(2, 30_000, 4.2, 3.5, 150, 10)]
BENCHMARKS = {"scc_k": {"top10": 90, "average": 170}, "fat_pct": {"top10": 4.6, "average": 4.4}, "protein_pct": {"top10": 3.7}}
PRICING = {
    "fat_eur_per_kg": 6.0, "protein_eur_per_kg": 8.0, "volume_charge_c_per_l": 3.0,
    "scc_bands": [{"max_k": 100, "adjustment_c": 0.5}, {"max_k": 400, "adjustment_c": 0}, {"adjustment_c": -1}],
    "tbc_bands": [{"max_k": 10, "adjustment_c": 0.25}, {"adjustment_c": 0}],
}
FULL = {"months": QUARTER, "milking_cows": 100, "hectares": 40, "benchmarks": BENCHMARKS, "pricing": PRICING}


def _quality(**overrides):
    return run_function("milk.quality", {**FULL, **overrides})


def test_weighted_period_and_solids():
    body = _quality()["result"]
    assert (body["from"]["month"], body["to"]["month"], body["month_count"]) == (1, 3, 3)
    assert body["period"] == {
        "milk_litres": 100_000, "fat_pct": 4.06, "protein_pct": 3.43, "scc_k": 345, "tbc_k": 9.8,
        "milk_solids_kg": 7_714.7, "kg_ms_per_cow": 77.15, "kg_ms_per_ha": 192.87,
    }


def test_eu_rolling_geometric_limits():
    months = _quality()["result"]["months"]
    assert [m["scc_rolling_k"] for m in months] == [300, round(geometric_mean([300, 150]), 2), 272.57]
    assert not any(m["scc_breach"] for m in months)
    high = _quality(months=[_month(1, 1_000, 4, 3.4, 500, 120), _month(2, 1_000, 4, 3.4, 450, 90)])["result"]
    assert [p["month"] for p in high["compliance"]["scc_breach_months"]] == [1, 2]
    # TBC: Feb rolling = √(120 × 90) = 103.92 > 100 → still a breach though Feb alone is 90.
    assert [p["month"] for p in high["compliance"]["tbc_breach_months"]] == [1, 2]


def test_rolling_window_follows_the_calendar():
    """A gap month is not filled: April's window (Feb–Apr) only holds April."""
    months = _quality(months=[_month(1, 1_000, 4, 3.4, 300, 9), _month(4, 1_000, 4, 3.4, 100, 9)])["result"]["months"]
    assert months[1]["scc_rolling_k"] == 100


def test_benchmark_gaps():
    gaps = _quality()["result"]["vs_benchmarks"]
    assert gaps["scc_k"] == {
        "farm": 345, "average": 170, "gap_to_average": 175, "position": "above", "better_than_average": False,
        "best20": None, "gap_to_best20": None, "better_than_best20": None,
        "top10": 90, "gap_to_top10": 255, "better_than_top10": False,
    }
    assert gaps["fat_pct"]["gap_to_top10"] == -0.54
    assert gaps["protein_pct"]["average"] is None
    assert "tbc_k" not in gaps
    good = _quality(benchmarks={"scc_k": {"top10": 400}})["result"]["vs_benchmarks"]["scc_k"]
    assert good["better_than_top10"] is True


def test_average_position_uses_the_about_band():
    """Tolerances: fat / protein ±0.05 pp, SCC ±10k, TBC ±2k (Dairy policy, ADR-0052).
    Farm: fat 4.06, protein 3.43, SCC 345, TBC 9.8."""
    benchmarks = {
        "fat_pct": {"average": 4.10},      # −0.04 → about
        "protein_pct": {"average": 3.30},  # +0.13 → above, better (higher pays more)
        "scc_k": {"average": 360},         # −15 → below, better (lower is better)
        "tbc_k": {"average": 7.8},         # +2.0 → about (edge of the band is inclusive)
    }
    gaps = _quality(benchmarks=benchmarks)["result"]["vs_benchmarks"]
    assert (gaps["fat_pct"]["position"], gaps["fat_pct"]["better_than_average"]) == ("about", None)
    assert (gaps["protein_pct"]["position"], gaps["protein_pct"]["better_than_average"]) == ("above", True)
    assert (gaps["scc_k"]["position"], gaps["scc_k"]["better_than_average"]) == ("below", True)
    assert (gaps["tbc_k"]["gap_to_average"], gaps["tbc_k"]["position"]) == (2.0, "about")
    assert gaps["fat_pct"]["top10"] is None and gaps["fat_pct"]["gap_to_top10"] is None


def test_best20_comparison():
    gaps = _quality(benchmarks={"scc_k": {"average": 170, "best20": 110}})["result"]["vs_benchmarks"]["scc_k"]
    assert (gaps["best20"], gaps["gap_to_best20"], gaps["better_than_best20"]) == (110, 235, False)


def test_gain_to_average():
    """Average fat 4.20 (+0.14), protein 3.40 (farm 3.43 already above → 0):
    100,000 × 1.03 × 0.14% = 144.2 kg × €6 = 865.20."""
    value = _quality(benchmarks={"fat_pct": {"average": 4.20}, "protein_pct": {"average": 3.40}})["result"]["value"]
    assert value["gain_to_average_eur"] == 865.2
    assert value["gain_to_top10_eur"] is None and value["gain_to_best20_eur"] is None


def test_component_value_bands_and_gains():
    value = _quality()["result"]["value"]
    assert (value["fat_eur"], value["protein_eur"], value["volume_charge_eur"]) == (25_090.8, 28_263.2, -3_000)
    assert (value["scc_adjustment_eur"], value["tbc_adjustment_eur"]) == (-600, 225)
    assert value["total_eur"] == 49_979
    assert value["price_c_per_l"]["total"] == 49.98
    assert value["gain_to_top10_eur"] == 5_562
    assert value["gain_at_best_band_eur"] == 1_125


def test_optional_blocks():
    body = _quality(benchmarks=None, pricing=None, milking_cows=None, hectares=None)["result"]
    assert body["vs_benchmarks"] is None and body["value"] is None
    assert body["period"]["kg_ms_per_cow"] is None
    no_top10 = _quality(benchmarks={"scc_k": {"average": 170}})["result"]["value"]
    assert no_top10["gain_to_top10_eur"] is None


def test_helpers_and_validation():
    assert weighted_mean([4.0, 4.2], [10, 30]) == 4.15
    assert weighted_mean([1], [0]) is None
    assert geometric_mean([0, 100]) == 0
    bad_bands = _quality(pricing={**PRICING, "scc_bands": [{"adjustment_c": 0}, {"max_k": 100, "adjustment_c": 1}]})
    assert bad_bands["error"]["details"]["reason"] == "bands_invalid"
    dup = _quality(months=[QUARTER[0], QUARTER[0]])
    assert dup["error"]["details"]["reason"] == "duplicate_period"
    missing = run_function("milk.quality", {"months": [{"year": 2026, "month": 1, "milk_litres": 1}]})
    assert missing["status"] == "needs_input"
    assert {m["path"] for m in missing["missing"]} == {
        "months[0].fat_pct", "months[0].protein_pct", "months[0].scc_k", "months[0].tbc_k"
    }


def test_http_matches_runner():
    body = client.post("/v1/functions/milk.quality/run", json=FULL).json()
    assert body == run_function("milk.quality", FULL)
