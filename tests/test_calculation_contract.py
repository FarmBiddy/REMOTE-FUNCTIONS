"""Stable public calculation ID contract — authoritative catalogue."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.provenance import SUPPORTED_CALCULATIONS, explain_annual_pnl
from farm_functions.domain import FinancialInput
from farm_functions.registry import (
    CALCULATION_CATALOGUE,
    FUNCTIONS,
    PUBLIC_CALCULATION_IDS,
    list_functions,
)
from farm_functions.runner import run_function

client = TestClient(app)

EXPECTED_PUBLIC_IDS = (
    "revenue.milk",
    "revenue.schemes",
    "revenue.other",
    "revenue.total",
    "costs.total",
    "profit.net",
    "profit.margin",
    "pl.summary",
    "pl.monthly",
    "pl.months",
    "cf.monthly",
    "cf.months",
    "loan.schedule",
    "pl.forecast",
    "cf.forecast",
)

MONTHLY_REFERENCE = {
    "year": 2026,
    "month": 3,
    "milk_litres": 40_000,
    "milk_price": 0.40,
    "biss": 2_000,
    "acres": 500,
    "cattle_sales": 1_000,
    "feed": 5_000,
    "fertiliser": 1_000,
    "loan_repayments": 1_500,
}

SAMPLE_MILK = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
}


def _happy_payload(calculation_id: str) -> dict:
    if calculation_id == "revenue.milk":
        return dict(SAMPLE_MILK)
    if calculation_id == "revenue.schemes":
        return {"biss": 20_000, "acres": 5_000, "other_grants": 0}
    if calculation_id == "revenue.other":
        return {"cattle_sales": 15_000, "land_leasing_income": 0, "other": 0}
    if calculation_id == "revenue.total":
        return {
            **SAMPLE_MILK,
            "biss": 20_000,
            "acres": 5_000,
            "other_grants": 0,
            "cattle_sales": 15_000,
            "land_leasing_income": 0,
            "other": 0,
        }
    if calculation_id == "costs.total":
        return {
            "feed": 80_000,
            "fertiliser": 15_000,
            "vet": 5_000,
            "contractor": 10_000,
            "labour": 40_000,
            "insurance": 4_000,
            "fuel": 6_000,
            "electricity": 3_000,
            "water": 0,
        }
    if calculation_id in ("profit.net", "profit.margin"):
        return {"revenue": 240_000, "costs": 163_000}
    if calculation_id == "pl.summary":
        return load_sample_inputs()
    if calculation_id == "pl.monthly":
        return dict(MONTHLY_REFERENCE)
    if calculation_id == "pl.months":
        return {"months": [dict(MONTHLY_REFERENCE)]}
    if calculation_id == "cf.monthly":
        return {"year": 2026, "month": 3, "milk": 18_000, "feed": 5_000}
    if calculation_id in ("pl.forecast", "cf.forecast"):
        item = {"year": 2025, "month": 10}
        if calculation_id == "pl.forecast":
            item |= {"milk_litres": 1, "milk_price": 1}
        return {"history": [item], "forecast": [{"year": 2026, "month": 10}]}
    if calculation_id == "loan.schedule":
        return {"balance": 1_200, "annual_rate": 0, "remaining_months": 12, "year": 2026, "month": 10}
    if calculation_id == "cf.months":
        return {"opening_cash": 0, "months": [{"year": 2026, "month": 3, "milk": 1}]}
    raise AssertionError(f"No happy payload for {calculation_id}")


def test_exactly_fifteen_unique_public_calculation_ids() -> None:
    assert PUBLIC_CALCULATION_IDS == EXPECTED_PUBLIC_IDS
    assert len(PUBLIC_CALCULATION_IDS) == 15
    assert len(set(PUBLIC_CALCULATION_IDS)) == 15
    assert tuple(c.id for c in CALCULATION_CATALOGUE) == EXPECTED_PUBLIC_IDS
    assert set(FUNCTIONS) == set(EXPECTED_PUBLIC_IDS)


def test_discovery_exposes_authoritative_catalogue_ids() -> None:
    discovered = [item["key"] for item in list_functions()]
    assert sorted(discovered) == sorted(EXPECTED_PUBLIC_IDS)

    response = client.get("/v1/functions")
    assert response.status_code == 200
    http_keys = [item["key"] for item in response.json()["functions"]]
    assert sorted(http_keys) == sorted(EXPECTED_PUBLIC_IDS)


def test_every_public_id_is_runnable() -> None:
    for calculation_id in PUBLIC_CALCULATION_IDS:
        result = run_function(calculation_id, _happy_payload(calculation_id))
        assert result["status"] == "ok", (calculation_id, result)
        assert result["function"] == calculation_id


def test_unknown_calculation_id_unchanged() -> None:
    runner = run_function("does.not.exist", {})
    assert runner["status"] == "error"
    assert runner["error"]["code"] == "unknown_calculation"
    assert "Unknown function" in runner["message"]

    response = client.post("/v1/functions/does.not.exist/run", json={})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_calculation"


def test_provenance_uses_catalogue_supported_ids() -> None:
    supported = {c.id for c in CALCULATION_CATALOGUE if c.supports_provenance}
    assert set(SUPPORTED_CALCULATIONS) == supported
    assert "pl.summary" not in supported
    assert "pl.monthly" not in supported

    provenance = explain_annual_pnl(
        FinancialInput.model_validate(load_sample_inputs())
    )
    assert set(provenance) == supported
    for calculation_id, entry in provenance.items():
        assert entry.calculation == calculation_id


def test_public_id_is_not_derived_from_handler_name() -> None:
    for spec in CALCULATION_CATALOGUE:
        assert spec.id == FUNCTIONS[spec.id].id
        assert spec.handler.__name__ != spec.id
        assert "." not in spec.handler.__name__ or spec.handler.__name__ != spec.id
