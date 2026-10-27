"""LIFELINE AI - dependent-organ graph for a town under disaster.

The town is modelled as a body:

    fuel_depot  -> BLOOD    (100 L diesel reserve)
    hospital    -> HEART    (70 L demand, 4 h of generator runtime left)
    water_pump  -> LUNGS    (30 L demand, fed from the hospital feeder)
    shelters    -> ORGANS   (200 people, no water until the pump runs)

`depends_on` in town.json means "cannot function unless this prerequisite
runs".  Because the chain is a DAG, Kahn's algorithm gives the only safe
funding order: fuel -> heart -> lungs -> organs.  If the heart fails, the
lungs and the organs fail with it.  That is the cascade the allocator has to
respect, and it is computed here, not guessed by a language model.

Run:  python dependency_graph.py
"""

from __future__ import annotations

import heapq
import json
import sys
from pathlib import Path
from typing import Iterable

TOWN_PATH = Path(__file__).with_name("town.json")


class DependencyError(ValueError):
    """Raised when town.json describes a graph that cannot be scheduled."""


class CycleError(DependencyError):
    """Raised when the dependency graph contains a cycle."""


def load_town(path: str | Path | None = None) -> dict:
    """Load and minimally validate the town model."""
    path = Path(path) if path else TOWN_PATH
    with path.open(encoding="utf-8") as fh:
        town = json.load(fh)

    organs = town.get("organs")
    if not isinstance(organs, dict) or not organs:
        raise DependencyError(f"{path}: missing 'organs' object")
    return town


def prerequisites(town: dict) -> dict[str, list[str]]:
    """Return node -> list of prerequisites (validated, order preserved)."""
    organs = town["organs"]
    graph: dict[str, list[str]] = {}
    for name, node in organs.items():
        deps = list(dict.fromkeys(node.get("depends_on", [])))  # dedupe, keep order
        for dep in deps:
            if dep not in organs:
                raise DependencyError(f"{name} depends on unknown organ '{dep}'")
            if dep == name:
                raise DependencyError(f"{name} depends on itself")
        graph[name] = deps
    return graph


def dependents(graph: dict[str, list[str]]) -> dict[str, list[str]]:
    """Invert the prerequisite graph: node -> organs that fail with it."""
    out: dict[str, list[str]] = {name: [] for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            out[dep].append(name)
    return out


def _priority(town: dict, name: str) -> int:
    """Lower number = more urgent. Unknown nodes sort last."""
    return int(town["organs"].get(name, {}).get("priority", 99))


def kahn_order(town: dict) -> list[str]:
    """Topological sort with Kahn's algorithm, urgent organs first on ties.

    A node becomes ready only when every prerequisite has been emitted, so
    the result is the order in which the town can actually be funded without
    powering a child from a dead parent.
    """
    graph = prerequisites(town)
    in_degree = {name: len(deps) for name, deps in graph.items()}

    ready: list[tuple[int, str]] = [
        (_priority(town, name), name) for name, degree in in_degree.items() if degree == 0
    ]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        _, name = heapq.heappop(ready)
        order.append(name)
        for child in dependents(graph)[name]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                heapq.heappush(ready, (_priority(town, child), child))

    if len(order) != len(graph):
        stuck = sorted(set(graph) - set(order))
        raise CycleError(f"dependency cycle among: {', '.join(stuck)}")
    return order


def cascade(town: dict, failed: Iterable[str]) -> dict:
    """Propagate failures downstream and report the blast radius.

    Returns the failed set, every organ that goes dark because of it, and the
    number of people who lose service.
    """
    graph = prerequisites(town)
    down = dependents(graph)
    failed = list(dict.fromkeys(failed))
    for name in failed:
        if name not in graph:
            raise DependencyError(f"unknown organ '{name}'")

    affected: list[str] = []
    seen: set[str] = set(failed)
    queue = list(failed)
    while queue:
        node = queue.pop(0)
        for child in down[node]:
            if child not in seen:
                seen.add(child)
                affected.append(child)
                queue.append(child)

    organs = town["organs"]
    people_lost = sum(
        int(organs[name].get("serves_people", organs[name].get("people", 0))) for name in affected
    )
    return {
        "failed": failed,
        "downstream_failed": affected,
        "total_down": failed + affected,
        "people_affected": people_lost,
        "note": "downstream failures are structural, not estimates",
    }


def funding_order(town: dict) -> list[dict]:
    """The hospital-first rule, expressed as an ordered funding plan.

    Order is topological (a child can never precede its parent) and, among
    organs that are simultaneously ready, the most urgent priority wins.
    """
    order = kahn_order(town)
    organs = town["organs"]
    plan = []
    for rank, name in enumerate(order, start=1):
        node = organs[name]
        plan.append(
            {
                "rank": rank,
                "organ": name,
                "role": node.get("role"),
                "priority": node.get("priority"),
                "demand_litres": node.get("fuel_demand_litres", 0),
                "rule": "fund before children" if dependents(prerequisites(town))[name] else "terminal",
            }
        )
    return plan


def critical_path(town: dict) -> dict:
    """Longest dependency chain, i.e. the slowest route to restore the town."""
    graph = prerequisites(town)
    memo: dict[str, list[str]] = {}

    def longest(name: str, trail: tuple[str, ...] = ()) -> list[str]:
        if name in trail:  # defensive; kahn_order already rejects cycles
            raise CycleError(f"dependency cycle through {name}")
        if name in memo:
            return memo[name]
        best = [name]
        for child in dependents(graph)[name]:
            candidate = [name] + longest(child, trail + (name,))
            if len(candidate) > len(best):
                best = candidate
        memo[name] = best
        return best

    paths = [longest(name) for name in graph]
    best = max(paths, key=len)
    return {"path": best, "depth": len(best) - 1}


def validate(town: dict) -> list[str]:
    """Return a list of human-readable problems (empty list = healthy)."""
    problems: list[str] = []
    organs = town.get("organs", {})
    try:
        prerequisites(town)
        kahn_order(town)
    except DependencyError as exc:
        problems.append(str(exc))
        return problems

    reserve = town.get("reserve", {}).get("total_litres")
    demand = sum(int(n.get("fuel_demand_litres", 0)) for n in organs.values())
    if reserve is not None and demand > reserve:
        problems.append(f"demand {demand} L exceeds reserve {reserve} L")
    if reserve is not None and demand < reserve:
        problems.append(f"unallocated surplus: demand {demand} L of {reserve} L reserve")
    return problems


def _bar(label: str, role: str, litres: int) -> str:
    filled = max(0, round(litres / 5))
    return f"  {label:12s} {role:6s} " + "#" * filled + f" {litres:3d}L"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    town = load_town()
    organs = town["organs"]

    print("LIFEGRID :: Kottur (%.4f N, %.4f E)" % (town["town"]["lat"], town["town"]["lon"]))
    print("fuel=blood  hospital=heart  pump=lungs  shelters=organs\n")

    print("DEPENDENCY CHAIN")
    for name in kahn_order(town):
        node = organs[name]
        if "fuel_demand_litres" in node:
            tag = f"{node['fuel_demand_litres']}L demand"
        elif "fuel_litres" in node:
            tag = f"{node['fuel_litres']}L reserve"
        else:
            tag = f"{node.get('people', 0)} people"
        print(f"  {name:12s} <- {', '.join(node.get('depends_on', [])) or 'source':12s}  [{tag}]")

    print("\nFUNDING ORDER (hospital first rule)")
    for step in funding_order(town):
        print(f"  {step['rank']}. {step['organ']:12s} priority {step['priority']}  {step['demand_litres']}L")

    cp = critical_path(town)
    print(f"\nCRITICAL PATH  {' -> '.join(cp['path'])}   (depth {cp['depth']})")

    blast = cascade(town, ["hospital"])
    print("\nWHAT-IF: hospital generator dies")
    print(f"  downstream failures : {', '.join(blast['downstream_failed']) or 'none'}")
    print(f"  people affected     : {blast['people_affected']}")

    print("\nRESERVE MAP")
    for name, node in organs.items():
        litres = node.get("fuel_demand_litres", node.get("fuel_litres", 0))
        print(_bar(name, node.get("role", ""), int(litres)))

    problems = validate(town)
    print("\nVALIDATION:", "ok" if not problems else "; ".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
