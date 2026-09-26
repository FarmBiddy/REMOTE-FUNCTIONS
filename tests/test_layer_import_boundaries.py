"""Layer import boundaries: Core / Agriculture / Dairy / Application dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FARM = REPO / "farm_functions"

_ORCHESTRATION_FORBIDDEN = (
    "farm_functions.calcs",
    "farm_functions.domain",
    "farm_functions.schemas",
    "farm_functions.provenance",
    "farm_functions.simulation",
    "farm_functions.scenarios",
    "farm_functions.loaders",
    "farm_functions.registry",
    "farm_functions.runner",
)

# Application/orchestration modules must resolve canonical packages, not calcs.
_APPLICATION_MODULES = (
    FARM / "registry.py",
    FARM / "provenance.py",
    FARM / "domain.py",
    FARM / "runner.py",
    FARM / "simulation.py",
    FARM / "scenarios.py",
    FARM / "errors.py",
    FARM / "schemas.py",
    FARM / "loaders" / "json_loader.py",
)

# Symbols that must not be owned/exported by Dairy (Core or Agriculture homes).
_DAIRY_MUST_NOT_EXPORT = frozenset(
    {
        "scheme_revenue",
        "net_profit",
        "profit_margin",
        "profit_margin_pct",
        "sum_amounts",
        "round_money",
        "round_margin_ratio",
        "round_margin_pct",
    }
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _defined_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _py_files(package: Path) -> list[Path]:
    return sorted(p for p in package.rglob("*.py") if p.is_file())


def _assert_no_forbidden(package: Path, forbidden_prefixes: tuple[str, ...]) -> None:
    for path in _py_files(package):
        for name in _imported_modules(path):
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ), f"{path.relative_to(REPO)} imports {name}"


def test_core_does_not_import_agriculture_or_dairy_or_calcs() -> None:
    _assert_no_forbidden(
        FARM / "core",
        ("farm_functions.agriculture", "farm_functions.dairy", *_ORCHESTRATION_FORBIDDEN),
    )


def test_agriculture_does_not_import_dairy_or_calcs() -> None:
    _assert_no_forbidden(
        FARM / "agriculture",
        ("farm_functions.dairy", *_ORCHESTRATION_FORBIDDEN),
    )


def test_dairy_does_not_import_orchestration() -> None:
    _assert_no_forbidden(FARM / "dairy", _ORCHESTRATION_FORBIDDEN)


def test_application_does_not_import_calcs_facade() -> None:
    """L5: orchestration resolves Dairy/Agriculture/Core directly (ADR-0017)."""
    for path in _APPLICATION_MODULES:
        for name in _imported_modules(path):
            assert name != "farm_functions.calcs" and not name.startswith(
                "farm_functions.calcs."
            ), f"{path.relative_to(REPO)} imports {name}"


def test_dairy_does_not_redefine_core_or_agriculture_formulas() -> None:
    """Dairy may *call* Core/Agriculture; it must not host a second body."""
    defined: set[str] = set()
    for path in _py_files(FARM / "dairy"):
        defined |= _defined_function_names(path)
    overlap = defined & _DAIRY_MUST_NOT_EXPORT
    assert not overlap, f"Dairy redefined generic symbols: {sorted(overlap)}"


def test_dairy_package_export_surface_excludes_generic_primitives() -> None:
    import farm_functions.dairy as dairy

    exported = set(dairy.__all__)
    overlap = exported & _DAIRY_MUST_NOT_EXPORT
    assert not overlap, f"Dairy __all__ exports generic symbols: {sorted(overlap)}"


def test_agriculture_scheme_revenue_matches_legacy_sum() -> None:
    from farm_functions.agriculture import scheme_revenue
    from farm_functions.calcs.revenue import scheme_revenue as via_calcs

    assert scheme_revenue(biss=20_000, acres=5_000, other_grants=0) == 25_000
    assert via_calcs(biss=20_000, acres=5_000) == 25_000
    assert scheme_revenue is via_calcs


def test_core_surplus_matches_calcs_profit_reexport() -> None:
    from farm_functions.calcs.profit import net_profit as via_calcs
    from farm_functions.core import net_profit

    assert net_profit(240_000, 163_000) == 77_000
    assert via_calcs(240_000, 163_000) == 77_000
    assert net_profit is via_calcs


def test_rounding_compat_reexport_identity() -> None:
    from farm_functions import rounding as compat
    from farm_functions.core import rounding as core_rounding

    assert compat.round_money is core_rounding.round_money
    assert compat.round_margin_ratio is core_rounding.round_margin_ratio
    assert compat.round_margin_pct is core_rounding.round_margin_pct


def test_dairy_milk_revenue_is_canonical_calcs_reexport() -> None:
    from farm_functions.calcs.revenue import milk_revenue as via_calcs
    from farm_functions.dairy.revenue import milk_revenue

    assert milk_revenue(100, 5000, 0.40) == 200_000
    assert via_calcs(100, 5000, 0.40) == 200_000
    assert milk_revenue is via_calcs


def test_dairy_costs_and_statement_reexport_identity() -> None:
    from farm_functions.calcs.costs import OPERATING_COST_CATEGORIES as via_calcs_cats
    from farm_functions.calcs.costs import total_costs as via_calcs_costs
    from farm_functions.calcs.summary import pl_summary as via_calcs_pl
    from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES, total_costs
    from farm_functions.dairy.statement import pl_summary

    assert OPERATING_COST_CATEGORIES is via_calcs_cats
    assert total_costs is via_calcs_costs
    assert pl_summary is via_calcs_pl
    assert "water" in OPERATING_COST_CATEGORIES
    assert "feed" in OPERATING_COST_CATEGORIES


def test_registry_binds_canonical_implementations() -> None:
    """Catalogue wiring uses Dairy / Agriculture / Core callables, not calcs bodies."""
    import farm_functions.registry as registry
    from farm_functions.agriculture.revenue import scheme_revenue
    from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct
    from farm_functions.dairy.costs import total_costs
    from farm_functions.dairy.revenue import milk_revenue, other_revenue, total_revenue
    from farm_functions.dairy.statement import pl_summary

    assert registry.milk_revenue is milk_revenue
    assert registry.scheme_revenue is scheme_revenue
    assert registry.other_revenue is other_revenue
    assert registry.total_revenue is total_revenue
    assert registry.total_costs is total_costs
    assert registry.net_profit is net_profit
    assert registry.profit_margin is profit_margin
    assert registry.profit_margin_pct is profit_margin_pct
    assert registry.pl_summary is pl_summary
    assert registry.FUNCTIONS["pl.summary"].handler is pl_summary


def test_statement_revenue_total_matches_dairy_total_revenue() -> None:
    """Statement composes the same Dairy revenue total as ``total_revenue``."""
    from farm_functions.dairy.revenue import total_revenue
    from farm_functions.dairy.statement import pl_summary

    kwargs = {
        "milking_cows": 100,
        "litres_per_cow": 5000,
        "milk_price": 0.40,
        "biss": 20_000,
        "acres": 5_000,
        "other_grants": 0,
        "cattle_sales": 15_000,
        "land_leasing_income": 0,
        "other": 0,
    }
    statement = pl_summary(**kwargs)
    assert statement["revenue"]["total"] == total_revenue(**kwargs)
    assert statement["revenue"]["schemes"] == 25_000.0


def test_provenance_agrees_with_canonical_and_runner() -> None:
    """Provenance values come from canonical formulas; match run_function publish path."""
    from farm_functions.agriculture.revenue import scheme_revenue
    from farm_functions.core.surplus import net_profit, profit_margin
    from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES, total_costs
    from farm_functions.dairy.revenue import milk_revenue, other_revenue, total_revenue
    from farm_functions.domain import FinancialInput
    from farm_functions.loaders.json_loader import load_sample_inputs
    from farm_functions.provenance import explain_annual_pnl
    from farm_functions.runner import run_function

    data = load_sample_inputs()
    explained = explain_annual_pnl(FinancialInput.model_validate(data))

    milk = milk_revenue(data["milking_cows"], data["litres_per_cow"], data["milk_price"])
    schemes = scheme_revenue(
        biss=data["biss"], acres=data["acres"], other_grants=data["other_grants"]
    )
    other = other_revenue(
        cattle_sales=data["cattle_sales"],
        land_leasing_income=data["land_leasing_income"],
        other=data["other"],
    )
    revenue = total_revenue(
        milking_cows=data["milking_cows"],
        litres_per_cow=data["litres_per_cow"],
        milk_price=data["milk_price"],
        biss=data["biss"],
        acres=data["acres"],
        other_grants=data["other_grants"],
        cattle_sales=data["cattle_sales"],
        land_leasing_income=data["land_leasing_income"],
        other=data["other"],
    )
    costs = total_costs(**{name: data[name] for name in OPERATING_COST_CATEGORIES})
    profit = net_profit(revenue, costs)
    margin = profit_margin(revenue, costs)

    assert explained["revenue.milk"].value == milk == 200_000.0
    assert explained["revenue.schemes"].value == schemes == 25_000.0
    assert explained["revenue.other"].value == other == 15_000.0
    assert explained["revenue.total"].value == revenue == 240_000.0
    assert explained["costs.total"].value == costs == 163_000.0
    assert explained["profit.net"].value == profit == 77_000.0
    assert explained["profit.margin"].value == margin

    summary = run_function("pl.summary", data)["result"]
    assert summary["revenue"]["total"] == 240_000.0
    assert summary["revenue"]["schemes"] == 25_000.0
    assert summary["costs"]["total"] == 163_000.0
    assert summary["profit"]["net"] == 77_000.0
    assert summary["profit"]["margin_pct"] == 32.08
    assert summary["finance"]["loan_repayments"] == 12_000.0


def test_sample_pl_summary_reference_unchanged() -> None:
    from farm_functions.loaders.json_loader import load_sample_inputs
    from farm_functions.runner import run_function

    result = run_function("pl.summary", load_sample_inputs())["result"]
    assert result["revenue"]["total"] == 240_000.0
    assert result["revenue"]["schemes"] == 25_000.0
    assert result["costs"]["total"] == 163_000.0
    assert result["profit"]["net"] == 77_000.0
    assert result["profit"]["margin_pct"] == 32.08
    assert result["finance"]["loan_repayments"] == 12_000.0
