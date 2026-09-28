"""Monthly Dairy Cash Flow composition (P3.2).

Calendar-blind: explicit cash floats only. Period identity is stamped by Domain.

Classification (operating / investing / financing) lives in these Dairy
catalogues — including Phase 1 placement of ``interest_paid`` under financing
outflows (ADR-0022 / D-CF1). Core only sums and nets amounts.

Does not derive cash from P&L composers or ``loan_repayments``.
"""

from farm_functions.core.cash import cash_section_net, net_cash_flow, sum_cash_amounts
from farm_functions.core.rounding import round_money

OPERATING_CASH_INFLOW_CATEGORIES = (
    "milk_receipts",
    "cattle_receipts",
    "scheme_receipts",
    "land_leasing_receipts",
    "other_operating_receipts",
)

OPERATING_CASH_OUTFLOW_CATEGORIES = (
    "feed_payments",
    "fertiliser_payments",
    "vet_payments",
    "contractor_payments",
    "labour_payments",
    "insurance_payments",
    "fuel_payments",
    "electricity_payments",
    "water_payments",
    "rent_lease_payments",
    "repairs_maintenance_payments",
    "professional_fees_payments",
    "levies_payments",
    "other_operating_payments",
)

INVESTING_CASH_INFLOW_CATEGORIES = ("asset_disposal_proceeds",)

INVESTING_CASH_OUTFLOW_CATEGORIES = (
    "machinery_equipment_payments",
    "other_capital_payments",
)

FINANCING_CASH_INFLOW_CATEGORIES = ("loan_proceeds",)

FINANCING_CASH_OUTFLOW_CATEGORIES = (
    "loan_principal_repayments",
    "interest_paid",
)


def _line_group(categories: tuple[str, ...], values: dict[str, float]) -> dict:
    lines = {name: round_money(float(values[name])) for name in categories}
    total = sum_cash_amounts(*(float(values[name]) for name in categories))
    return {"lines": lines, "total": round_money(total)}


def _activity_section(
    inflow_categories: tuple[str, ...],
    outflow_categories: tuple[str, ...],
    values: dict[str, float],
) -> dict:
    inflows = _line_group(inflow_categories, values)
    outflows = _line_group(outflow_categories, values)
    in_raw = sum_cash_amounts(*(float(values[n]) for n in inflow_categories))
    out_raw = sum_cash_amounts(*(float(values[n]) for n in outflow_categories))
    return {
        "inflows": inflows,
        "outflows": outflows,
        "net": round_money(cash_section_net(in_raw, out_raw)),
    }


def monthly_cash_flow(
    milk_receipts: float = 0,
    cattle_receipts: float = 0,
    scheme_receipts: float = 0,
    land_leasing_receipts: float = 0,
    other_operating_receipts: float = 0,
    feed_payments: float = 0,
    fertiliser_payments: float = 0,
    vet_payments: float = 0,
    contractor_payments: float = 0,
    labour_payments: float = 0,
    insurance_payments: float = 0,
    fuel_payments: float = 0,
    electricity_payments: float = 0,
    water_payments: float = 0,
    rent_lease_payments: float = 0,
    repairs_maintenance_payments: float = 0,
    professional_fees_payments: float = 0,
    levies_payments: float = 0,
    other_operating_payments: float = 0,
    asset_disposal_proceeds: float = 0,
    machinery_equipment_payments: float = 0,
    other_capital_payments: float = 0,
    loan_proceeds: float = 0,
    loan_principal_repayments: float = 0,
    interest_paid: float = 0,
) -> dict:
    """Compose one monthly Dairy Cash Flow from explicit cash drivers.

    Returns money payload only (no ``period`` key).
    """
    values = {
        "milk_receipts": milk_receipts,
        "cattle_receipts": cattle_receipts,
        "scheme_receipts": scheme_receipts,
        "land_leasing_receipts": land_leasing_receipts,
        "other_operating_receipts": other_operating_receipts,
        "feed_payments": feed_payments,
        "fertiliser_payments": fertiliser_payments,
        "vet_payments": vet_payments,
        "contractor_payments": contractor_payments,
        "labour_payments": labour_payments,
        "insurance_payments": insurance_payments,
        "fuel_payments": fuel_payments,
        "electricity_payments": electricity_payments,
        "water_payments": water_payments,
        "rent_lease_payments": rent_lease_payments,
        "repairs_maintenance_payments": repairs_maintenance_payments,
        "professional_fees_payments": professional_fees_payments,
        "levies_payments": levies_payments,
        "other_operating_payments": other_operating_payments,
        "asset_disposal_proceeds": asset_disposal_proceeds,
        "machinery_equipment_payments": machinery_equipment_payments,
        "other_capital_payments": other_capital_payments,
        "loan_proceeds": loan_proceeds,
        "loan_principal_repayments": loan_principal_repayments,
        "interest_paid": interest_paid,
    }
    operating = _activity_section(
        OPERATING_CASH_INFLOW_CATEGORIES,
        OPERATING_CASH_OUTFLOW_CATEGORIES,
        values,
    )
    investing = _activity_section(
        INVESTING_CASH_INFLOW_CATEGORIES,
        INVESTING_CASH_OUTFLOW_CATEGORIES,
        values,
    )
    financing = _activity_section(
        FINANCING_CASH_INFLOW_CATEGORIES,
        FINANCING_CASH_OUTFLOW_CATEGORIES,
        values,
    )
    op_in = sum_cash_amounts(*(float(values[n]) for n in OPERATING_CASH_INFLOW_CATEGORIES))
    inv_in = sum_cash_amounts(*(float(values[n]) for n in INVESTING_CASH_INFLOW_CATEGORIES))
    fin_in = sum_cash_amounts(*(float(values[n]) for n in FINANCING_CASH_INFLOW_CATEGORIES))
    op_out = sum_cash_amounts(*(float(values[n]) for n in OPERATING_CASH_OUTFLOW_CATEGORIES))
    inv_out = sum_cash_amounts(*(float(values[n]) for n in INVESTING_CASH_OUTFLOW_CATEGORIES))
    fin_out = sum_cash_amounts(*(float(values[n]) for n in FINANCING_CASH_OUTFLOW_CATEGORIES))
    cash_in_raw = sum_cash_amounts(op_in, inv_in, fin_in)
    cash_out_raw = sum_cash_amounts(op_out, inv_out, fin_out)
    return {
        "currency": "EUR",
        "operating": operating,
        "investing": investing,
        "financing": financing,
        "cash_in": round_money(cash_in_raw),
        "cash_out": round_money(cash_out_raw),
        "net_cash_flow": round_money(net_cash_flow(cash_in_raw, cash_out_raw)),
    }


__all__ = [
    "FINANCING_CASH_INFLOW_CATEGORIES",
    "FINANCING_CASH_OUTFLOW_CATEGORIES",
    "INVESTING_CASH_INFLOW_CATEGORIES",
    "INVESTING_CASH_OUTFLOW_CATEGORIES",
    "OPERATING_CASH_INFLOW_CATEGORIES",
    "OPERATING_CASH_OUTFLOW_CATEGORIES",
    "monthly_cash_flow",
]
