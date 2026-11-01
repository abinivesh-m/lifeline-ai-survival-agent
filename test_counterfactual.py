"""The counterfactual grid is a claim like any other.

    python -m pytest test_counterfactual.py -q

The console on the page does not compute: it reads `ui/public/data/counterfactuals.json`
and prints what it finds. That is only honest if the file is what the solver
actually produces, so this file rebuilds the whole grid from
`field_reports.replan` and `allocator.validate_proposal` and compares row for row.

A stale row is therefore a failing build, not a number a judge cannot check.
"""

from __future__ import annotations

import json
from pathlib import Path

import counterfactual

ROOT = Path(__file__).parent
GRID = json.loads((ROOT / "ui" / "public" / "data" / "counterfactuals.json").read_text(encoding="utf-8"))
ARTEFACT = json.loads((ROOT / "artifacts" / "counterfactuals.json").read_text(encoding="utf-8"))


def _row(reserve: int, road: str, operator: str = "none") -> dict:
    return next(
        r for r in GRID["rows"]
        if r["reserve_litres"] == reserve and r["village_road"] == road and r["operator"] == operator
    )


def test_the_two_copies_of_the_grid_are_identical() -> None:
    """The page reads one file and the repo keeps another. They cannot drift."""
    assert GRID == ARTEFACT


def test_every_row_is_what_the_solver_still_produces() -> None:
    fresh = counterfactual.build()
    assert len(fresh["rows"]) == len(GRID["rows"]) > 0
    for stored, rebuilt in zip(GRID["rows"], fresh["rows"]):
        assert rebuilt == stored, f"{stored['id']} no longer matches the solver"


def test_the_base_world_is_the_seventy_thirty_plan() -> None:
    base = _row(100, "open")
    assert base["allocation"] == {"hospital": 70, "water_pump": 30}
    assert base["total_litres"] == 100
    assert base["route_km"] == 7.8
    assert base["pump_hours"] == 6.0
    assert base["water_litres_lost"] == 0
    assert base["validator"] == []


def test_closing_the_village_road_costs_exactly_one_block() -> None:
    """The 1.82 L detour, floored to the 5 L unit, takes one block off the lungs."""
    blocked = _row(100, "blocked")
    assert blocked["route_km"] == 13.0
    assert blocked["route_fuel_litres"] == 4.55
    assert blocked["reserve_in_force"] == 95
    assert blocked["allocation"] == {"hospital": 70, "water_pump": 25}
    assert blocked["pump_hours"] == 5.0
    assert blocked["water_litres_lost"] == 4000
    assert blocked["heart_protected"] is True


def test_below_the_pump_threshold_the_lungs_get_nothing() -> None:
    """The cliff is real: once the heart is fed, there is no block left for the lungs."""
    assert _row(75, "open")["allocation"].get("water_pump") == 5
    assert _row(70, "open")["allocation"].get("water_pump", 0) == 0
    assert _row(70, "open")["water_litres_lost"] == 24000


def test_the_heart_is_the_last_thing_to_be_shorted() -> None:
    """No row ever funds the lungs while the hospital is below its stated demand."""
    for row in GRID["rows"]:
        hospital = row["allocation"].get("hospital", 0)
        pump = row["allocation"].get("water_pump", 0)
        assert not (hospital < 70 and pump > 0), f"{row['id']} starves the heart to feed the lungs"


def test_every_allocation_sums_to_the_reserve_in_force() -> None:
    for row in GRID["rows"]:
        assert row["total_litres"] == row["reserve_in_force"], row["id"]


def test_the_operator_is_refused_in_every_world() -> None:
    """A human instruction never becomes the plan, and the reason is always named."""
    overrides = [r for r in GRID["rows"] if r["operator"] == "pump_first"]
    assert len(overrides) > 0
    for row in overrides:
        assert row["override_refused"] is True, row["id"]
        assert row["override_reasons"], f"{row['id']} refuses without saying why"
        assert row["applied_instead"] == row["allocation"], row["id"]


def test_the_grid_covers_both_roads_and_every_reserve() -> None:
    assert {r["reserve_litres"] for r in GRID["rows"]} == set(counterfactual.RESERVES)
    assert {r["village_road"] for r in GRID["rows"]} == set(counterfactual.ROADS)
    assert {r["operator"] for r in GRID["rows"]} == set(counterfactual.OPERATORS)
    assert len(GRID["rows"]) == len(counterfactual.RESERVES) * len(counterfactual.ROADS) * len(counterfactual.OPERATORS)


def test_no_row_is_a_model_claim() -> None:
    """The grid is the deterministic core. Nothing here may come from a model."""
    for row in GRID["rows"]:
        assert "model" not in row, row["id"]
        assert "provider" not in row, row["id"]
        assert row["status"] in {"no_change", "replanned"}, row["id"]
