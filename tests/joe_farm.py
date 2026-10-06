"""Joe Bloggs: a realistic Irish spring-calving dairy farm used by the end-to-end test.

100 cows, ~500,000 L a year; little milk in winter, peak in May. Milk cheques are
paid the month after supply. BISS advance in October, balance in December; ACRES
in June and December. Loans match the platform prototype (AIB variable / fixed).
Reporting year: Oct 2025 – Sep 2026; prior year: Oct 2024 – Sep 2025.
"""

LITRES = {1: 4_000, 2: 22_000, 3: 48_000, 4: 62_000, 5: 70_000, 6: 66_000,
          7: 60_000, 8: 54_000, 9: 46_000, 10: 38_000, 11: 24_000, 12: 8_000}
PRICE = {10: 0.48, 11: 0.47, 12: 0.46, 1: 0.45, 2: 0.45, 3: 0.44,
         4: 0.43, 5: 0.42, 6: 0.42, 7: 0.43, 8: 0.44, 9: 0.46}
FEED = {1: 7_000, 2: 9_000, 3: 10_000, 4: 6_000, 5: 4_000, 6: 3_500,
        7: 3_500, 8: 4_000, 9: 5_000, 10: 6_000, 11: 7_000, 12: 7_500}
FERTILISER = {2: 3_000, 3: 6_000, 4: 5_000, 5: 3_000, 6: 2_000, 7: 1_500, 8: 1_000}
VET = {2: 2_500, 3: 2_000}
CONTRACTOR = {5: 4_000, 6: 6_000, 8: 3_000, 9: 2_000}
BISS = {10: 9_000, 12: 3_400}
ACRES = {6: 2_000, 12: 4_000}
CATTLE = {2: 2_000, 3: 3_000, 4: 2_500, 9: 4_000, 10: 3_000}
MONTHS = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # Oct → Sep


def _year(month: int, start_year: int) -> int:
    return start_year if month >= 10 else start_year + 1


def pl_month(month: int, start_year: int, price_uplift: float = 0.0) -> dict:
    return {
        "year": _year(month, start_year),
        "month": month,
        "milk_litres": LITRES[month],
        "milk_price": round(PRICE[month] + price_uplift, 4),
        "biss": BISS.get(month, 0),
        "acres": ACRES.get(month, 0),
        "cattle_sales": CATTLE.get(month, 0),
        "feed": FEED[month],
        "fertiliser": FERTILISER.get(month, 0),
        "vet": VET.get(month, 600),
        "contractor": CONTRACTOR.get(month, 300),
        "labour": 3_500,
        "insurance": 400,
        "fuel": 700,
        "electricity": 900,
        "repairs_maintenance": 600,
        "rent_lease": 1_000,
        "professional_fees": 2_400 if month == 12 else 0,
        "levies": 150,
        "loan_repayments": 1_525,
    }


PRIOR = [pl_month(m, 2024, price_uplift=0.03) for m in MONTHS]  # Oct 2024 – Sep 2025
ACTUAL = [pl_month(m, 2025) for m in MONTHS]  # Oct 2025 – Sep 2026

_COST_LINES = ("feed", "fertiliser", "vet", "contractor", "labour", "insurance", "fuel",
               "electricity", "repairs_maintenance", "rent_lease", "professional_fees", "levies")


def cash_month(pl: dict, previous_pl: dict) -> dict:
    """Same month's costs and schemes; milk cheque for the previous month's supply."""
    return {
        "year": pl["year"],
        "month": pl["month"],
        "milk": round(previous_pl["milk_litres"] * previous_pl["milk_price"], 2),
        **{k: pl[k] for k in ("biss", "acres", "cattle_sales", *_COST_LINES)},
        "interest_paid": 330,
        "loan_principal_repayments": 1_195,
        "household_drawings": 2_500,
        "machinery_equipment_payments": 6_000 if (pl["year"], pl["month"]) == (2026, 7) else 0,
    }


CASH = [cash_month(pl, prev) for pl, prev in zip(ACTUAL, [PRIOR[-1], *ACTUAL[:-1]])]
OPENING_CASH = 15_000  # bank balance at 1 Oct 2025

LOANS = [  # as at 30 Sep 2026; next instalments in October
    {"balance": 68_400, "annual_rate": 0.042, "remaining_months": 63, "year": 2026, "month": 10,
     "original_principal": 120_000, "variable": True},
    {"balance": 18_400, "annual_rate": 0.051, "remaining_months": 29, "year": 2026, "month": 10,
     "original_principal": 38_000},
]
ASSETS = [
    {"category": "buildings", "cost": 240_000, "year": 2015, "month": 1, "life_months": 300},
    {"category": "buildings", "cost": 120_000, "year": 2018, "month": 3, "life_months": 240},
    {"category": "machinery", "cost": 95_000, "year": 2024, "month": 3, "method": "reducing_balance", "annual_rate": 0.15},
    {"category": "machinery", "cost": 6_000, "year": 2026, "month": 7, "life_months": 60},
]
VALUES = {
    "livestock": 342_000, "livestock_opening_value": 330_000,
    "stock": 11_000, "stock_opening_value": 9_000,
    "land": 1_600_000, "debtors": 21_000, "creditors": 12_490,
}
HOUSEHOLD = {"drawings": 30_000, "tax": 7_000, "off_farm_income": 0}
COWS = 100
HECTARES = 60
