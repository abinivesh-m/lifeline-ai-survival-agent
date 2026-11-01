"""Counterfactual grid: one solver, many worlds.

    python counterfactual.py            # rebuild the grid
    python counterfactual.py --print    # show it

The console on the page does not compute anything. It looks up a row in
`ui/public/data/counterfactuals.json`, and every row in that file was produced
here by the same A* search and the same priority solver the agent runs at
incident time. `test_counterfactual.py` re-derives the whole grid from the
solver, so a stale row fails CI instead of showing a judge a number the code no
longer produces.

Two axes, because they are the two things that actually change during a flood:

* `reserve_litres` - how much diesel survived the depot damage
* `village_road`   - whether the 7.8 km shortcut is still open

and one operator axis, because the interesting claim is a refusal:

* `pump_first`     - a human insists the pump outranks the hospital

No model is called. No network is touched. This is the deterministic core, run
over a lattice instead of once.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import allocator
import field_reports

ROOT = Path(__file__).parent
OUT = ROOT / "artifacts" / "counterfactuals.json"
UI_OUT = ROOT / "ui" / "public" / "data" / "counterfactuals.json"

RESERVES = list(range(100, 25, -5))
ROADS = ["open", "blocked"]
OPERATORS = ["none", "pump_first"]
VILLAGE_ROAD = "Kottur village road"
PUMP_ASK_LITRES = 40


def _constraints(reserve: int, road: str, base_reserve: int) -> list[dict[str, Any]]:
    """The world, expressed in the same typed constraints a phone call produces."""
    out: list[dict[str, Any]] = []
    if reserve < base_reserve:
        out.append({
            "kind": "depot_litres",
            "value": reserve,
            "unit": "L",
            "span": f"counterfactual: {base_reserve - reserve} L lost with the depot",
            "source": "counterfactual",
            "confidence": 1.0,
        })
    if road == "blocked":
        out.append({
            "kind": "road_blocked",
            "value": VILLAGE_ROAD,
            "unit": None,
            "span": f"counterfactual: {VILLAGE_ROAD} is under water",
            "source": "counterfactual",
            "confidence": 1.0,
        })
    return out


def _row(town: dict, reserve: int, road: str, operator: str) -> dict[str, Any]:
    base_reserve = int(town["reserve"]["total_litres"])
    constraints = _constraints(reserve, road, base_reserve)
    result = field_reports.replan(town, constraints)

    # The base cell produces no constraints, so replan returns the short
    # "no_change" shape. Read the same fields off the base plan instead of
    # inventing a second solver path.
    if result["status"] == "no_change":
        allocation = result["allocation_before"]
        route_km = result["route_before"]["distance_km"]
        route_fuel = result["route_before"]["fuel_litres"]
        reserve_in_force = base_reserve
        pump_hours = field_reports._pump_hours(int(allocation.get("water_pump", 0)), town)
        water_lost = 0
        problems: list[str] = []
        changes: list[dict[str, Any]] = []
    else:
        allocation = result.get("allocation_after") or {}
        route_km = result.get("route_km_after")
        route_fuel = result.get("route_fuel_after")
        reserve_in_force = result.get("reserve_after")
        pump_hours = result.get("pump_hours_after")
        water_lost = result.get("water_litres_lost")
        problems = result.get("validator", [])
        changes = [
            {"kind": c["kind"], "before": c["before"], "after": c["after"]}
            for c in result.get("changes", [])
        ]

    in_force = copy.deepcopy(town)
    in_force["reserve"]["total_litres"] = int(reserve_in_force or base_reserve)

    row: dict[str, Any] = {
        "id": f"r{reserve:03d}-{road}-{operator}",
        "reserve_litres": reserve,
        "village_road": road,
        "operator": operator,
        "status": result["status"],
        "route_km": route_km,
        "route_fuel_litres": route_fuel,
        "reserve_in_force": reserve_in_force,
        "allocation": allocation,
        "total_litres": sum(allocation.values()),
        "pump_hours": pump_hours,
        "water_litres_lost": water_lost,
        "heart_protected": allocation.get("hospital") == int(town["organs"]["hospital"]["fuel_demand_litres"]),
        "validator": problems,
        "changes": changes,
    }

    if operator == "pump_first":
        # The human instruction is the same shape whatever the reserve: "the
        # pump gets 40 L, the hospital gets the rest". That keeps the refusal
        # about priority, not about arithmetic.
        pump = min(PUMP_ASK_LITRES, int(reserve_in_force or base_reserve))
        forced = {"hospital": int(reserve_in_force or base_reserve) - pump, "water_pump": pump}
        rejected = allocator.validate_proposal(forced, in_force)
        row["instruction"] = forced
        row["override_refused"] = bool(rejected)
        row["override_reasons"] = rejected
        row["applied_instead"] = allocation
    return row


def build(town: dict | None = None) -> dict[str, Any]:
    town = town or allocator.load_town()
    rows = [_row(town, reserve, road, operator) for reserve in RESERVES for road in ROADS for operator in OPERATORS]
    return {
        "generated_from": "counterfactual.py - field_reports.replan + allocator.policy_solve + allocator.validate_proposal",
        "axes": {
            "reserve_litres": RESERVES,
            "village_road": ROADS,
            "operator": OPERATORS,
        },
        "base": {
            "reserve_litres": int(town["reserve"]["total_litres"]),
            "village_road": VILLAGE_ROAD,
            "hospital_demand_litres": int(town["organs"]["hospital"]["fuel_demand_litres"]),
            "pump_demand_litres": int(town["organs"]["water_pump"]["fuel_demand_litres"]),
        },
        "rows": rows,
        "note": (
            "Every row is the deterministic solver re-run against a different world, not a curve fitted "
            "to one. The validator verdict is the same code that rejects a model proposal."
        ),
    }


def write() -> dict[str, Any]:
    grid = build()
    body = json.dumps(grid, indent=2, ensure_ascii=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    UI_OUT.parent.mkdir(parents=True, exist_ok=True)
    UI_OUT.write_text(body, encoding="utf-8")
    return grid


def _print(grid: dict[str, Any]) -> None:
    print(f"{'reserve':>7} {'road':>8} {'operator':>11} {'heart':>6} {'lungs':>6} "
          f"{'total':>6} {'pump h':>7} {'water lost':>11}  verdict")
    for row in grid["rows"]:
        alloc = row["allocation"]
        verdict = "PASS" if not row["validator"] else f"{len(row['validator'])} problem(s)"
        if row.get("override_refused"):
            verdict = f"REFUSED ({len(row['override_reasons'])} reasons)"
        print(
            f"{row['reserve_litres']:>7} {row['village_road']:>8} {row['operator']:>11} "
            f"{alloc.get('hospital', 0):>6} {alloc.get('water_pump', 0):>6} "
            f"{row['total_litres']:>6} {row['pump_hours']:>7} {row['water_litres_lost']:>11}  {verdict}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="counterfactual grid for the console")
    parser.add_argument("--print", action="store_true", help="print the grid and do not write")
    args = parser.parse_args(argv)

    if args.print:
        _print(build())
        return 0

    grid = write()
    _print(grid)
    print(f"\n{len(grid['rows'])} rows written to {OUT.relative_to(ROOT)} and {UI_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
