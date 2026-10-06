"""Report bundles for the bank, the advisor and the accountant (ADR-0041).

Application layer, composition only: every section is the output of an
existing calculation run on the shared farm file. No new formulas here; the
Platform renders the bundle (PDF, screens).
"""

from __future__ import annotations

from typing import Any

from farm_functions.accounts import bs_summary, pl_net
from farm_functions.assets import assets_schedule
from farm_functions.compare import cf_statements, compare_pl, pl_statements, sum_statements
from farm_functions.core.rounding import round_margin_pct, round_money
from farm_functions.core.surplus import profit_margin_pct
from farm_functions.kpis import kpi_summary
from farm_functions.loans import debt_capacity, schedule_loans
from farm_functions.sensitivity import cash_roll, risk_sensitivity


def _span(months: list[dict[str, Any]]) -> tuple[tuple[int, int], tuple[int, int]]:
    keys = sorted((m["year"], m["month"]) for m in months)
    return keys[0], keys[-1]


def _period(key: tuple[int, int]) -> dict[str, Any]:
    return {"kind": "month", "year": key[0], "month": key[1]}


def _header(report: str, f: dict[str, Any]) -> dict[str, Any]:
    first, last = _span(f["pl_months"])
    return {
        "report": report,
        "currency": "EUR",
        "as_of": _period(last),
        "period": {"from": _period(first), "to": _period(last), "month_count": len(f["pl_months"])},
    }


def _cash(f: dict[str, Any]) -> dict[str, Any]:
    """Actual cash rolled from ``opening_cash``; projection rolled on from its close."""
    actual = cash_roll(f["cf_months"], f["opening_cash"])
    projection = (
        cash_roll(f["projected_cf_months"], actual["closing_cash"]) if f["projected_cf_months"] else None
    )
    return {"actual": actual, "projection": projection}


def _depreciation_and_assets(f: dict[str, Any]) -> dict[str, Any] | None:
    if not f["assets"]:
        return None
    (fy, fm), (ty, tm) = _span(f["pl_months"])
    return assets_schedule(assets=f["assets"], from_year=fy, from_month=fm, to_year=ty, to_month=tm)


def _profit(f: dict[str, Any], fixed_assets: dict[str, Any] | None) -> dict[str, Any]:
    # Interest of the period = interest actually paid (cash), the best record we hold.
    interest = sum_statements(cf_statements(f["cf_months"]))["financing"]["outflows"]["lines"]["interest_paid"]
    return pl_net(
        months=f["pl_months"],
        depreciation=fixed_assets["total"]["depreciation"] if fixed_assets else 0.0,
        interest=interest,
        livestock_opening_value=(
            f["livestock"] if f["livestock_opening_value"] is None else f["livestock_opening_value"]
        ),
        livestock_closing_value=f["livestock"],
        stock_opening_value=f["stock"] if f["stock_opening_value"] is None else f["stock_opening_value"],
        stock_closing_value=f["stock"],
    )


def _balance_sheet(f: dict[str, Any], closing_cash: float) -> dict[str, Any]:
    _, (year, month) = _span(f["pl_months"])
    return bs_summary(
        year=year,
        month=month,
        cash=closing_cash,
        debtors=f["debtors"],
        stock=f["stock"],
        livestock=f["livestock"],
        land=f["land"],
        creditors=f["creditors"],
        other_long_term_liabilities=f["other_long_term_liabilities"],
        loans=f["loans"],
        assets=f["assets"],
    )


def _loans(f: dict[str, Any]) -> dict[str, Any] | None:
    return schedule_loans(loans=f["loans"]) if f["loans"] else None


def _kpis(f: dict[str, Any], loans: dict[str, Any] | None) -> dict[str, Any]:
    return kpi_summary(
        months=f["pl_months"],
        milking_cows=f["milking_cows"],
        milk_solids_kg=f["milk_solids_kg"],
        hectares=f["hectares"],
        debt_balance=loans["total_balance"] if loans else None,
    )


def report_bank(**f: Any) -> dict[str, Any]:
    """``report.bank``: profit, debt service, borrowing capacity, balance sheet, cash outlook."""
    fixed_assets = _depreciation_and_assets(f)
    loans = _loans(f)
    cash = _cash(f)
    terms = f["new_loan"] or {"annual_rate": 0.0, "term_months": 1, "min_cover": 1.0}
    capacity = debt_capacity(
        months=f["pl_months"],
        drawings=f["drawings"],
        tax=f["tax"],
        off_farm_income=f["off_farm_income"],
        **terms,
    )
    if f["new_loan"] is None:  # capacity without an application: no loan sizing
        capacity["new_loan"] = None
    return {
        **_header("bank", f),
        "profit": _profit(f, fixed_assets),
        "kpis": _kpis(f, loans),
        "loans": loans,
        "capacity": capacity,
        "balance_sheet": _balance_sheet(f, cash["actual"]["closing_cash"]),
        "cash": cash,
    }


def report_advisor(**f: Any) -> dict[str, Any]:
    """``report.advisor``: KPIs, profit, vs prior year, what-ifs (forward when projected)."""
    loans = _loans(f)
    projected = bool(f["projected_pl_months"] and f["projected_cf_months"])
    pl_months = f["pl_months"] + (f["projected_pl_months"] if projected else [])
    cf_months = f["cf_months"] + (f["projected_cf_months"] if projected else [])
    start = min((m["year"], m["month"]) for m in f["projected_pl_months"]) if projected else (None, None)
    return {
        **_header("advisor", f),
        "kpis": _kpis(f, loans),
        "profit": _profit(f, _depreciation_and_assets(f)),
        "comparison": (
            compare_pl(actual=f["pl_months"], comparison=f["prior_pl_months"]) if f["prior_pl_months"] else None
        ),
        "sensitivity": risk_sensitivity(
            pl_months=pl_months,
            cf_months=cf_months,
            opening_cash=f["opening_cash"],
            scenarios=f["scenarios"],
            shocks_from_year=start[0],
            shocks_from_month=start[1],
        ),
    }


def report_accountant(**f: Any) -> dict[str, Any]:
    """``report.accountant``: P&L by line, net profit, fixed asset note, balance sheet, cash flow."""
    fixed_assets = _depreciation_and_assets(f)
    statement = sum_statements(pl_statements(f["pl_months"]))
    margin = profit_margin_pct(statement["revenue"]["total"], statement["costs"]["total"])
    cash = cash_roll(f["cf_months"], f["opening_cash"])
    cash_flow = sum_statements(cf_statements(f["cf_months"]))
    return {
        **_header("accountant", f),
        "profit_and_loss": {
            **_round_tree(statement),
            "margin_pct": round_margin_pct(margin),
        },
        "net_profit": _profit(f, fixed_assets),
        "fixed_assets": fixed_assets,
        "balance_sheet": _balance_sheet(f, cash["closing_cash"]),
        "cash_flow": {
            **_round_tree(cash_flow),
            "opening_cash": cash["opening_cash"],
            "closing_cash": cash["closing_cash"],
        },
    }


def _round_tree(tree: dict[str, Any]) -> dict[str, Any]:
    return {k: _round_tree(v) if isinstance(v, dict) else round_money(v) for k, v in tree.items()}
