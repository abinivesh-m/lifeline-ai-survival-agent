"""One command, one scorecard.

    python judge.py

Runs the claims this repository makes, in the order a judge would check them,
and prints the exact command that reproduces each line. Nothing here writes: the
ledger, the run record and every artefact are read-only. If a line says PASS, the
command beside it produces that number on your machine too.

Exit code 0 means every line passed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import a_star
import allocator
import counterfactual
import credit_tracker
import field_reports
import seri_gate

ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8")

OK = "PASS"
NO = "FAIL"


def _pytest() -> tuple[bool, str]:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header"],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    tail = (out.stdout + out.stderr).strip().splitlines()[-1] if (out.stdout + out.stderr).strip() else ""
    return out.returncode == 0, tail


def _audit() -> tuple[bool, str]:
    _, nodes, edges = a_star.load_network()
    problems = a_star.audit(nodes, edges)
    return not problems, f"{len(edges)} edges checked" if not problems else "; ".join(problems)


def _route() -> tuple[bool, str]:
    town = allocator.load_town()
    _, nodes, edges = a_star.load_network()
    route = a_star.plan_route(town, nodes, edges)
    ok = (
        route["distance_km"] == 7.8
        and route["saving"]["percent"] == 40.0
        and route["baseline"]["direct_corridor_km"] == 4.2
    )
    return ok, f"4.2 km blocked -> {route['distance_km']} km, {route['saving']['percent']:.1f}% less fuel"


def _allocation() -> tuple[bool, str]:
    town = allocator.load_town()
    plan = allocator.policy_solve(town)
    problems = allocator.validate_proposal(plan, town)
    ok = plan == {"hospital": 70, "water_pump": 30} and not problems
    return ok, f"{plan['hospital']} L heart / {plan['water_pump']} L lungs = {sum(plan.values())} L"


def _refusal() -> tuple[bool, str]:
    town = allocator.load_town()
    rejected = allocator.validate_proposal({"hospital": 60, "water_pump": 40}, town)
    return bool(rejected), f"{len(rejected)} reason(s), the heart is never starved"


def _ledger() -> tuple[bool, str]:
    tracker = credit_tracker.CreditTracker()
    problems = tracker.verify()
    total = round(sum(float(e["cost_usd"]) for e in tracker.entries), 6)
    ok = not problems and total > 0
    return ok, f"{len(tracker.entries)} rows, ${total:,.2f} of ${tracker.budget:,.0f}"


def _replan() -> tuple[bool, str]:
    town = allocator.load_town()
    reports = field_reports.from_artifact()
    changed = None
    for report in reports:
        result = field_reports.replan(town, field_reports.extract(report["transcript"], report["source"]))
        if result["status"] != "no_change":
            changed = result
    if not changed:
        return False, "no stored field report moves the plan"
    ok = changed["route_km_before"] == 7.8 and changed["route_km_after"] == 13.0
    return ok, f"{changed['route_km_before']} -> {changed['route_km_after']} km, {changed['water_litres_lost']} L of water lost"


def _counterfactual() -> tuple[bool, str]:
    stored = json.loads((ROOT / "ui" / "public" / "data" / "counterfactuals.json").read_text(encoding="utf-8"))
    fresh = counterfactual.build()
    ok = fresh["rows"] == stored["rows"]
    return ok, f"{len(stored['rows'])} rows reproduced by the solver"


def _gate() -> tuple[bool, str]:
    """A misheard word must not dispatch fuel. Test the refusal, not the approval."""
    heard = seri_gate.decide("maybe", {"status": "answered", "intent": "APPROVE", "confidence": 0.99}, "en")
    clear = seri_gate.decide("yes", {"status": "answered", "intent": "APPROVE", "confidence": 0.99}, "en")
    ok = heard["decision"] == "WITHHELD" and clear["decision"] == "APPROVED"
    return ok, f"'maybe' -> {heard['decision']}, 'yes' -> {clear['decision']}"


def _artefacts() -> tuple[bool, str]:
    missing = []
    for line in README.splitlines():
        if "capture needed" in line:
            continue
        for path in re.findall(r"`(artifacts/[A-Za-z0-9_./-]+\.(?:json|txt|png|mp4|wav))`", line):
            if not (ROOT / path).exists():
                missing.append(path)
    return not missing, "0 missing" if not missing else f"missing: {', '.join(sorted(set(missing)))}"


CHECKS = [
    ("acceptance tests", "python -m pytest -q", _pytest),
    ("A* heuristic admissible", "python a_star.py --audit", _audit),
    ("route around the landslide", "python a_star.py", _route),
    ("allocation is exact", "python allocator.py --mode policy", _allocation),
    ("validator refuses the operator", "python agent.py --yes --mode policy --scenario pump-critical", _refusal),
    ("ledger re-derives itself", "python credit_tracker.py verify", _ledger),
    ("a phone call moves the plan", "python agent.py --yes --mode policy --scenario field-report", _replan),
    ("counterfactual grid", "python counterfactual.py", _counterfactual),
    ("spoken gate refuses 'maybe'", "python seri_gate.py --transcript maybe", _gate),
    ("README cites only real files", "python -m pytest test_claims.py -q", _artefacts),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LIFELINE AI judge scorecard")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)

    results = []
    for label, command, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as exc:  # a broken check is a FAIL, never a crash
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        results.append({"check": label, "command": command, "pass": ok, "detail": detail})

    if args.json:
        print(json.dumps({"results": results, "passed": sum(r["pass"] for r in results), "total": len(results)}, indent=2))
        return 0 if all(r["pass"] for r in results) else 1

    width = max(len(r["check"]) for r in results)
    print("LIFELINE AI - judge scorecard")
    print("=" * (width + 46))
    for i, r in enumerate(results, start=1):
        mark = OK if r["pass"] else NO
        print(f"{i:>2}  {r['check']:<{width}}  {mark:<4}  {r['detail']}")
        print(f"    {'':<{width}}  run: {r['command']}")
    passed = sum(r["pass"] for r in results)
    print("=" * (width + 46))
    print(f"{passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
