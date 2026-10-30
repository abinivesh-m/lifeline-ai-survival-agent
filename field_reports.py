"""LIFELINE AI - field report -> typed constraint -> replan.

The gap this closes
-------------------
Step 2 (LISTEN) transcribed a Tamil call into an artefact. Step 8 (REPLAN) moved
the plan when the world changed. The two never touched: a transcript sat on disk
and the replan waited for a CLI flag. So the "agent" listened and, separately,
recovered - which is not the same as listening *in order to* recover.

This module is the join. A transcript becomes a list of typed constraints, each
one carrying the exact span of words that produced it; the constraints mutate a
copy of the town; the route and the allocation are then recomputed by the same
solver the base plan uses.

Why the extraction is regex and not a model call
------------------------------------------------
A transcript that can say "the hospital needs forty litres" must never be able
to invent a number that moves a town's last diesel. The model transcribes; code
decides what the words are allowed to change. Unknown phrasing yields no
constraint - never a guess. That is the same division of labour as the allocator:
the model proposes, code disposes.

Constraint kinds
----------------
    road_blocked    a named road is closed, so the A* network loses those edges
    closure_hours   how long the closure lasts, which bounds the fuel needed
    depot_litres    the depot itself lost fuel

Run:
    python field_reports.py --transcript "the village road is washed out"
    python field_reports.py --from-artifact          # every stored report
    python field_reports.py --self-test
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from pathlib import Path
from typing import Any

import a_star
import allocator

ROOT = Path(__file__).parent
REPORTS = ROOT / "artifacts" / "voice_reports.json"
OUT = ROOT / "artifacts" / "field_replan.json"

# Road names as they are written in town.json, plus how a caller might say them.
ROAD_ALIASES: dict[str, str] = {
    "village road": "Kottur village road",
    "kottur village road": "Kottur village road",
    "grama salai": "Kottur village road",
    "கிராமச் சாலை": "Kottur village road",
    "கிராம சாலை": "Kottur village road",
    "nh-544": "NH-544",
    "nh 544": "NH-544",
    "nh544": "NH-544",
    "km 42": "NH-544 km 42",
    "bypass": "Kottur bypass",
    "feeder road": "pump feeder road",
    "pump feeder": "pump feeder road",
    "shelter link": "shelter link",
    "south link": "Kottur south link",
}

BLOCKED_WORDS = (
    "blocked", "closed", "gone", "washed out", "washed away", "collapsed",
    "impassable", "cannot use", "can't use", "unreachable", "under water",
    "flooded", "no road", "cut off",
    "மூட", "சேத", "உடை", "முடியாது", "வெள்ள", "சாலை இல்ல",
)

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "ஒன்று": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5,
    "ஆறு": 6, "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10,
}

HOUR_WORDS = ("hour", "hours", "hr", "hrs", "மணி")
LITRE_WORDS = ("litre", "litres", "liter", "liters", "லிட்டர்")
DEPOT_WORDS = ("depot", "tank", "reserve", "டிப்போ", "டேங்க்", "இருப்பு")


def _number(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def _span(text: str, match: re.Match[str], pad: int = 0) -> str:
    start = max(0, match.start() - pad)
    end = min(len(text), match.end() + pad)
    return text[start:end].strip()


def extract(transcript: str, source: str = "report") -> list[dict[str, Any]]:
    """Turn one transcript into typed constraints. No model call, no guessing."""
    if not transcript:
        return []

    low = transcript.lower()
    found: list[dict[str, Any]] = []

    # -- road_blocked ------------------------------------------------------ #
    # A road is only blocked if the transcript names it *and* says it is shut.
    # The window is taken around the blocking word, not the road name: a caller
    # says "km 42 ... the road is closed", so the closure often follows the name.
    # Longest alias wins, so "kottur village road" is not also read as "village road".
    aliases = sorted(ROAD_ALIASES, key=len, reverse=True)
    claimed: set[str] = set()
    for word in BLOCKED_WORDS:
        start = low.find(word)
        while start != -1:
            window = low[max(0, start - 70): start + len(word) + 70]
            alias = next((a for a in aliases if a in window), None)
            if alias:
                road = ROAD_ALIASES[alias]
                if road not in claimed:
                    claimed.add(road)
                    found.append({
                        "kind": "road_blocked",
                        "value": road,
                        "unit": None,
                        "span": transcript[max(0, start - 25): start + len(word) + 25].strip(),
                        "source": source,
                        "confidence": 0.9,
                    })
                break
            start = low.find(word, start + 1)

    # -- closure_hours ----------------------------------------------------- #
    hours = re.search(
        r"(\d{1,2}|" + "|".join(map(re.escape, NUMBER_WORDS)) + r")\s*("
        + "|".join(HOUR_WORDS) + r")",
        low,
    )
    if hours:
        value = _number(hours.group(1))
        if value:
            found.append({
                "kind": "closure_hours",
                "value": value,
                "unit": "h",
                "span": _span(transcript, hours),
                "source": source,
                "confidence": 0.85,
            })

    # -- depot_litres ------------------------------------------------------ #
    # Only a loss is actionable, so require a depot word and a litre figure.
    if any(w in low for w in DEPOT_WORDS):
        litres = re.search(
            r"(\d{1,3}|" + "|".join(map(re.escape, NUMBER_WORDS)) + r")\s*("
            + "|".join(LITRE_WORDS) + r")",
            low,
        )
        if litres:
            value = _number(litres.group(1))
            if value:
                found.append({
                    "kind": "depot_litres",
                    "value": value,
                    "unit": "L",
                    "span": _span(transcript, litres, pad=12),
                    "source": source,
                    "confidence": 0.85,
                })

    return found


def _edges_from(town: dict) -> list[a_star.Edge]:
    """Rebuild Edge objects after the town copy has been mutated."""
    return [
        a_star.Edge(
            src=e["from"],
            dst=e["to"],
            km=float(e["km"]),
            road=e["road"],
            status=e.get("status", "open"),
            reason=e.get("reason"),
        )
        for e in town["road_network"]["edges"]
    ]


def apply_constraints(town: dict, constraints: list[dict]) -> tuple[dict, list[dict]]:
    """Apply constraints to a copy of the town. Returns (town_copy, changes)."""
    work = copy.deepcopy(town)
    changes: list[dict] = []

    for c in constraints:
        kind = c["kind"]

        if kind == "road_blocked":
            road = c["value"]
            hit = 0
            for edge in work["road_network"]["edges"]:
                if edge["road"] != road or edge.get("status") == "blocked":
                    continue
                edge["status"] = "blocked"
                edge["reason"] = f"field report: {c['span'][:80]}"
                hit += 1
            if hit:
                changes.append({
                    "kind": kind,
                    "before": "open",
                    "after": "blocked",
                    "detail": f"{hit} edge(s) on {road}",
                    "span": c["span"],
                })

        elif kind == "closure_hours":
            before = work["crisis"]["expected_clear_hours"]
            work["crisis"]["expected_clear_hours"] = c["value"]
            if before != c["value"]:
                changes.append({
                    "kind": kind,
                    "before": before,
                    "after": c["value"],
                    "detail": "expected clear time",
                    "span": c["span"],
                })

        elif kind == "depot_litres":
            before = work["reserve"]["total_litres"]
            if c["value"] < before:
                work["reserve"]["total_litres"] = c["value"]
                changes.append({
                    "kind": kind,
                    "before": before,
                    "after": c["value"],
                    "detail": "usable diesel in the depot",
                    "span": c["span"],
                })

    return work, changes


def _pump_hours(litres: int, town: dict) -> float:
    rate = float(town["organs"]["water_pump"]["fuel_l_per_hour"])
    return round(litres / rate, 1) if rate else 0.0


def replan(town: dict, constraints: list[dict], plan: dict | None = None) -> dict[str, Any]:
    """Re-solve route and allocation against the constrained world.

    `plan` is the base run's step-5 result when the caller has it; without it the
    base is recomputed with the deterministic solver, which is what the offline
    path uses anyway.
    """
    _, nodes, _ = a_star.load_network()
    base_route = a_star.plan_route(town, nodes, _edges_from(town))
    base_allocation = (
        dict(plan["allocation"]) if plan and plan.get("allocation") else allocator.policy_solve(town)
    )

    if not constraints:
        return {
            "status": "no_change",
            "constraints": [],
            "changes": [],
            "detail": "no actionable constraint in the transcript",
            "route_before": base_route,
            "allocation_before": base_allocation,
            "evidence": "extraction is regex over the verbatim transcript, no model call",
        }

    work, changes = apply_constraints(town, constraints)
    reserve_original = int(town["reserve"]["total_litres"])
    reserve_constrained = int(work["reserve"]["total_litres"])
    unit = int(town["allocation_policy"]["min_unit_litres"])

    try:
        route_after = a_star.plan_route(work, nodes, _edges_from(work))
    except a_star.RoutingError as exc:
        return {
            "status": "unroutable",
            "constraints": constraints,
            "changes": changes,
            "detail": f"no open road reaches the hospital: {exc}",
            "allocation_before": base_allocation,
            "allocation_after": None,
            "evidence": "A* raised RoutingError on the constrained network",
        }

    # Fuel accounting, stated rather than hidden: the base plan does not charge
    # delivery fuel, so the replan charges only the increase this report added.
    extra_fuel = round(route_after["fuel_litres"] - base_route["fuel_litres"], 3)
    reserve_after = reserve_constrained
    if extra_fuel > 0:
        usable = reserve_constrained - extra_fuel
        reserve_after = int(math.floor(usable / unit) * unit)
        work["reserve"]["total_litres"] = reserve_after
        changes.append({
            "kind": "delivery_fuel",
            "before": reserve_constrained,
            "after": reserve_after,
            "detail": (
                f"the detour burns {extra_fuel} L more ({route_after['fuel_litres']} vs "
                f"{base_route['fuel_litres']} L); floored to the {unit} L unit, that is "
                f"{reserve_constrained - reserve_after} L off the organ budget"
            ),
            "span": None,
        })

    allocation_after = allocator.policy_solve(work)
    problems = allocator.validate_proposal(allocation_after, work)

    pump_before = int(base_allocation.get("water_pump", 0))
    pump_after = int(allocation_after.get("water_pump", 0))
    hours_before = _pump_hours(pump_before, town)
    hours_after = _pump_hours(pump_after, town)
    per_hour = int(town["organs"]["water_pump"]["delivers_litres_per_hour"])

    # A longer closure needs fuel the reserve does not have. Report the size of
    # the hole; never quietly re-scale the hospital's demand to make it fit.
    base_hours = int(town["crisis"]["expected_clear_hours"])
    now_hours = int(work["crisis"]["expected_clear_hours"])
    generator_lph = float(town["organs"]["hospital"]["generator_l_per_hour"])
    shortfall = round(max(0, now_hours - base_hours) * generator_lph, 1)

    status = "shortfall" if shortfall > 0 else "replanned"
    if not changes:
        status = "no_change"

    return {
        "status": status,
        "constraints": constraints,
        "changes": changes,
        "route_before": base_route,
        "route_after": route_after,
        "route_km_before": base_route["distance_km"],
        "route_km_after": route_after["distance_km"],
        "route_fuel_before": base_route["fuel_litres"],
        "route_fuel_after": route_after["fuel_litres"],
        "reserve_before": reserve_original,
        "reserve_after": reserve_after,
        "allocation_before": base_allocation,
        "allocation_after": allocation_after,
        "validator": problems,
        "pump_hours_before": hours_before,
        "pump_hours_after": hours_after,
        "water_litres_lost": round(max(0.0, hours_before - hours_after) * per_hour),
        "closure_hours_before": base_hours,
        "closure_hours_after": now_hours,
        "shortfall_litres": shortfall,
        "fuel_accounting": (
            "the base plan does not charge delivery fuel; the replan charges only the "
            "increase the new constraint introduced, rounded to the minimum unit"
        ),
        "evidence": "same A* search and same priority solver as the base plan, no model call",
    }


def from_artifact(path: Path = REPORTS) -> list[dict]:
    """Every stored report, as (transcript, source) pairs."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"transcript": r.get("transcript", ""), "source": r.get("file") or f"report_{i}"}
        for i, r in enumerate(data.get("reports", []), start=1)
    ]


def _fmt(result: dict) -> str:
    lines = [f"status: {result['status']}"]
    for c in result.get("constraints", []):
        lines.append(f"  constraint {c['kind']} = {c['value']} {c['unit'] or ''}".rstrip())
        lines.append(f"    from: \"{c['span']}\"")
    for ch in result.get("changes", []):
        lines.append(f"  changed {ch['kind']}: {ch['before']} -> {ch['after']}  ({ch['detail']})")
    if result.get("allocation_after"):
        lines.append(f"  route    {result['route_km_before']} km -> {result['route_km_after']} km")
        lines.append(f"  fuel     {result['route_fuel_before']} L -> {result['route_fuel_after']} L")
        lines.append(f"  reserve  {result['reserve_before']} L -> {result['reserve_after']} L")
        lines.append(f"  plan     {result['allocation_before']} -> {result['allocation_after']}")
        lines.append(
            f"  pump     {result['pump_hours_before']} h -> {result['pump_hours_after']} h"
            f", {result['water_litres_lost']} L of water lost"
        )
    if result.get("shortfall_litres"):
        lines.append(f"  shortfall {result['shortfall_litres']} L the reserve cannot cover")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="field report -> constraint -> replan")
    parser.add_argument("--transcript", help="one report, quoted")
    parser.add_argument("--from-artifact", action="store_true", help="use every stored report")
    parser.add_argument("--write", action="store_true", help=f"write {OUT.name}")
    args = parser.parse_args(argv)

    town = allocator.load_town()
    reports = (
        from_artifact()
        if args.from_artifact
        else [{"transcript": args.transcript or "", "source": "cli"}]
    )
    if not reports:
        print("no reports")
        return 1

    results = []
    for report in reports:
        constraints = extract(report["transcript"], source=report["source"])
        result = replan(town, constraints)
        result["transcript"] = report["transcript"]
        result["source"] = report["source"]
        results.append(result)
        print(f"\n=== {report['source']} ===")
        print(f'  "{report["transcript"][:120]}"')
        print(_fmt(result))

    if args.write:
        OUT.write_text(json.dumps({"schema": "lifeline.field_replan/1.0", "runs": results}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
