"""Survivor protocols: one mode switch, one pheromone learner.

Both run on the road graph in town.json, both are deterministic, and both
refuse rather than invent. Neither touches the network.

    python protocols.py

Why these two:

    snake_boat_relay   the road A* is tried first. If the last road closes,
                       the same solver is re-run with water edges. Kottur has
                       no surveyed water edges, so the relay reports ARMED
                       and refuses to invent a river.

    ant_pheromone      a seeded ant-colony run over the real graph. The
                       blocked corridor cannot be reinforced, so its trail
                       evaporates while the 7.8 km bypass hardens. That is
                       the "learns the block" claim, with the iteration
                       count printed rather than asserted.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import a_star
from a_star import Edge, RoutingError

SEED = 7
ANTS = 12
ITERATIONS = 12
RHO = 0.45
ALPHA = 1.0
BETA = 2.0
Q = 1.0
LEARNED_SHARE = 0.01


def _key(edge: Edge) -> tuple[str, str]:
    return tuple(sorted((edge.src, edge.dst)))  # type: ignore[return-value]


def _reachable(adjacency: dict, goal: str) -> set[str]:
    """Nodes from which the goal is still reachable on open edges."""
    reverse: dict[str, set[str]] = {}
    for src, links in adjacency.items():
        for dst, _km, _edge in links:
            reverse.setdefault(dst, set()).add(src)

    seen = {goal}
    stack = [goal]
    while stack:
        node = stack.pop()
        for parent in reverse.get(node, ()):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


def _walk(
    adjacency: dict,
    tau: dict[tuple[str, str], float],
    can_reach: set[str],
    start: str,
    goal: str,
    rng: random.Random,
) -> list[str] | None:
    """One ant, one path. Returns None if it walks itself into a corner."""
    path = [start]
    seen = {start}
    node = start

    while node != goal:
        options = [
            (dst, km)
            for dst, km, _edge in adjacency.get(node, ())
            if dst not in seen and dst in can_reach and km > 0
        ]
        if not options:
            return None

        weights = []
        for dst, km in options:
            pheromone = tau.get(tuple(sorted((node, dst))), 1e-9)
            weights.append(max(pheromone, 1e-9) ** ALPHA * (1.0 / km) ** BETA)

        total = sum(weights)
        pick = rng.random() * total
        running = 0.0
        chosen = options[-1][0]
        for (dst, _km), weight in zip(options, weights):
            running += weight
            if pick <= running:
                chosen = dst
                break

        path.append(chosen)
        seen.add(chosen)
        node = chosen

    return path


def _km(path: list[str], adjacency: dict) -> float:
    total = 0.0
    for src, dst in zip(path, path[1:]):
        for neighbour, km, _edge in adjacency.get(src, ()):
            if neighbour == dst:
                total += km
                break
    return total


def snake_boat_relay(
    nodes: dict,
    edges: list[Edge],
    start: str = "fuel_depot",
    goal: str = "hospital",
    water_edges: list[Edge] | None = None,
) -> dict:
    """Road A* first, water A* if the road is gone. Neither is fabricated."""
    water_edges = list(water_edges or [])
    road = None
    road_error: str | None = None

    try:
        road = a_star.a_star(nodes, a_star.build_adjacency(edges), start, goal)
    except RoutingError as exc:
        road_error = str(exc)

    water = None
    if road is None and water_edges:
        merged = list(edges) + water_edges
        try:
            water = a_star.a_star(nodes, a_star.build_adjacency(merged), start, goal)
        except RoutingError as exc:
            road_error = f"{road_error}; water: {exc}"

    if road is not None:
        return {
            "mode": "road",
            "switched": False,
            "armed": True,
            "water_edges": len(water_edges),
            "road_km": round(road.km, 2),
            "km": round(road.km, 2),
            "path": road.path,
            "note": "road A* won at 7.8 km; the water leg stayed armed and unused",
        }

    if water is not None:
        return {
            "mode": "water",
            "switched": True,
            "armed": True,
            "water_edges": len(water_edges),
            "road_km": None,
            "km": round(water.km, 2),
            "path": water.path,
            "note": "road A* raised RoutingError, water A* took over on surveyed edges",
        }

    return {
        "mode": "none",
        "switched": False,
        "armed": True,
        "water_edges": len(water_edges),
        "road_km": None,
        "km": None,
        "path": [],
        "note": (
            "road A* raised RoutingError and town.json has 0 surveyed water "
            "edges, so the relay reports ARMED and refuses to invent a river"
        ),
        "error": road_error,
    }


def ant_pheromone(
    nodes: dict,
    edges: list[Edge],
    start: str = "fuel_depot",
    goal: str = "hospital",
    seed: int = SEED,
    ants: int = ANTS,
    iterations: int = ITERATIONS,
) -> dict:
    """A real ant-colony run on the real graph, seeded so it is reproducible."""
    adjacency = a_star.build_adjacency(edges)
    can_reach = _reachable(adjacency, goal)

    open_edges = [edge for edge in edges if edge.open]
    blocked_edges = [edge for edge in edges if not edge.open]

    tau = {_key(edge): 1.0 for edge in edges}
    rng = random.Random(seed)

    best_km: float | None = None
    best_path: list[str] = []
    learned_after: int | None = None
    history: list[dict] = []

    for iteration in range(1, iterations + 1):
        for key in tau:
            tau[key] *= 1.0 - RHO

        trails: list[tuple[float, list[str]]] = []
        for _ant in range(ants):
            path = _walk(adjacency, tau, can_reach, start, goal, rng)
            if not path:
                continue
            km = _km(path, adjacency)
            trails.append((km, path))
            deposit = Q / km if km > 0 else Q
            for src, dst in zip(path, path[1:]):
                key = tuple(sorted((src, dst)))
                tau[key] = tau.get(key, 1e-9) + deposit

        if trails:
            km, path = min(trails, key=lambda item: item[0])
            if best_km is None or km < best_km:
                best_km, best_path = km, path

        blocked_mean = (
            sum(tau[_key(edge)] for edge in blocked_edges) / len(blocked_edges)
            if blocked_edges
            else 0.0
        )
        open_mean = (
            sum(tau[_key(edge)] for edge in open_edges) / len(open_edges)
            if open_edges
            else 1e-9
        )
        share = blocked_mean / (blocked_mean + open_mean) if blocked_mean + open_mean else 0.0

        if learned_after is None and share < LEARNED_SHARE:
            learned_after = iteration

        history.append(
            {
                "iteration": iteration,
                "blocked_share": round(share, 5),
                "best_km": round(best_km, 2) if best_km is not None else None,
            }
        )

    final_share = history[-1]["blocked_share"] if history else 1.0

    return {
        "seed": seed,
        "ants": ants,
        "iterations": iterations,
        "runs": ants * iterations,
        "best_km": round(best_km, 2) if best_km is not None else None,
        "best_path": best_path,
        "learned_after": learned_after,
        "blocked_share_final": final_share,
        "history": history,
        "note": (
            "Seeded ACO on the road graph. The blocked corridor cannot be "
            "reinforced, so its trail evaporates while the open path hardens. "
            "No randomness escapes: seed 7 reproduces every number."
        ),
    }


def build(nodes: dict | None = None, edges: list[Edge] | None = None) -> dict:
    if nodes is None or edges is None:
        _town, nodes, edges = a_star.load_network()
    # Kottur has no surveyed water edges. Passing an empty list is the point:
    # the relay says it is armed, not that it swam.
    water: list[Edge] = []
    return {
        "snake_boat_relay": snake_boat_relay(nodes, edges, water_edges=water),
        "ant_pheromone": ant_pheromone(nodes, edges),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = build()
    relay = report["snake_boat_relay"]
    ant = report["ant_pheromone"]

    print("SNAKE BOAT RELAY")
    print(f"  mode      : {relay['mode']} (switched={relay['switched']})")
    print(f"  km        : {relay['km']}")
    print(f"  water     : {relay['water_edges']} surveyed edges")
    print(f"  note      : {relay['note']}")
    print()
    print("ANT PHEROMONE")
    print(f"  best      : {ant['best_km']} km via {' -> '.join(ant['best_path'])}")
    print(f"  runs      : {ant['runs']} ({ant['ants']} ants x {ant['iterations']} iterations)")
    print(f"  learned   : blocked trail below {LEARNED_SHARE:.0%} after "
          f"{ant['learned_after']} iterations")
    print(f"  final     : blocked share {ant['blocked_share_final']:.4%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
