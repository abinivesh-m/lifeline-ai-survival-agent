"""LIFELINE AI - the 8-step survival agent, end to end.

    step 1  PERCEIVE   SAM 3.1    flood extent from imagery        (artifact adapter)
    step 2  LISTEN     Voice      Tamil field reports              (artifact adapter)
    step 3  GRAPH      code       dependency order + cascade       deterministic
    step 4  ROUTE      code       A* around the landslide          deterministic
    step 5  ALLOCATE   Wonder     evidence -> 70 L / 30 L           model + validator
    step 6  BUDGET     code       $150 ledger, 80%/95% alerts       deterministic
    step 7  APPROVE    human      nothing executes without a yes   gate
    step 8  REPLAN     code       new constraint -> new plan       deterministic

Steps 1 and 2 read captured model output from artifacts/. Until those files
exist they report PENDING instead of inventing numbers - the run is still
complete because steps 3-8 do not depend on them.

    python agent.py                 # interactive approval gate
    python agent.py --yes           # recording mode: pre-approve, still logged
    python agent.py --scenario pump-critical

Runs are written to runs/latest.json as evidence for the submission.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import a_star
import allocator
import credit_tracker
import dependency_graph

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"
RUNS = ROOT / "runs"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _read_artifact(name: str) -> dict | None:
    path = ARTIFACTS / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _rule(title: str) -> None:
    print(f"\n{'-' * 68}\n{title}\n{'-' * 68}")


def _lifegrid(town: dict) -> str:
    o = town["organs"]
    return (
        f"  LIFEGRID :: {town['town']['name']} "
        f"({town['town']['lat']:.4f} N, {town['town']['lon']:.4f} E)\n\n"
        f"   fuel_depot [BLOOD {o['fuel_depot']['fuel_litres']}L]\n"
        f"        |\n"
        f"        v\n"
        f"   hospital   [HEART {o['hospital']['fuel_demand_litres']}L  "
        f"{o['hospital']['runtime_hours_left']:g}h left]\n"
        f"        |\n"
        f"        v\n"
        f"   water_pump [LUNGS {o['water_pump']['fuel_demand_litres']}L]\n"
        f"        |\n"
        f"        v\n"
        f"   shelters   [ORGANS {o['shelters']['people']} people, no water]"
    )


# --------------------------------------------------------------------------- #
# the eight steps
# --------------------------------------------------------------------------- #

def step_perceive(town: dict) -> dict:
    artifact = _read_artifact("sam_flood_segments.json")
    if artifact is None:
        return {
            "step": 1,
            "name": "PERCEIVE",
            "model": "sam-3.1",
            "status": "pending_capture",
            "detail": "artifacts/sam_flood_segments.json not captured yet (Day 2)",
        }

    frames = artifact.get("frames", [])
    severity = [f.get("water_severity_percent") for f in frames if f.get("water_severity_percent") is not None]
    return {
        "step": 1,
        "name": "PERCEIVE",
        "model": "sam-3.1",
        "status": "ok",
        "frames": len(frames),
        "water_severity_percent": severity,
        "worst_frame": max(frames, key=lambda f: f.get("water_severity_percent", 0), default=None),
        "evidence": "pixel masks returned by sam-3.1, stored verbatim in artifacts/",
    }


def step_listen(town: dict) -> dict:
    artifact = _read_artifact("voice_reports.json")
    if artifact is None:
        return {
            "step": 2,
            "name": "LISTEN",
            "model": "muse-voice-transcribe-1.0",
            "status": "pending_capture",
            "detail": "artifacts/voice_reports.json not captured yet (Day 2)",
        }

    reports = artifact.get("reports", [])
    blocked = [r for r in reports if "block" in r.get("transcript", "").lower()]
    return {
        "step": 2,
        "name": "LISTEN",
        "model": "muse-voice-transcribe-1.0",
        "status": "ok",
        "reports": len(reports),
        "blocked_mentions": len(blocked),
        "sample": reports[0].get("transcript") if reports else None,
        "evidence": "verbatim transcripts, Tamil original kept alongside English",
    }


def step_graph(town: dict) -> dict:
    order = dependency_graph.kahn_order(town)
    blast = dependency_graph.cascade(town, ["hospital"])
    return {
        "step": 3,
        "name": "GRAPH",
        "status": "ok",
        "order": order,
        "critical_path": dependency_graph.critical_path(town)["path"],
        "if_hospital_fails": blast["downstream_failed"],
        "people_affected": blast["people_affected"],
        "evidence": "Kahn topological sort over town.json depends_on edges",
    }


def step_route(town: dict) -> dict:
    _, nodes, edges = a_star.load_network()
    report = a_star.plan_route(town, nodes, edges)
    return {
        "step": 4,
        "name": "ROUTE",
        "status": "ok",
        **report,
    }


def step_allocate(town: dict, mode: str, log_credit: bool) -> dict:
    result = allocator.allocate(town, mode=mode, log_credit=log_credit)
    return {"step": 5, "name": "ALLOCATE", "status": "ok", **result}


def step_budget(town: dict) -> dict:
    tracker = credit_tracker.CreditTracker()
    status = tracker.status()
    return {
        "step": 6,
        "name": "BUDGET",
        "status": "ok",
        "spent_usd": status["spent_usd"],
        "remaining_usd": status["remaining_usd"],
        "percent_used": status["percent_used"],
        "level": status["level"],
        "alerts": status["alerts"],
        "plan_usd": credit_tracker.PLANNED_TOTAL,
        "evidence": "credit_usage.json, append-only, one row per model call",
    }


def step_approve(allocation: dict, town: dict, auto: bool) -> dict:
    print("\n  Proposed plan:")
    for organ, litres in allocation["allocation"].items():
        label = town["organs"][organ]["label"]
        print(f"    {litres:3d} L -> {label}")
    print(f"    {allocation['total']:3d} L total, nothing executed yet")

    if auto:
        print("\n  APPROVED via --yes (recording mode, logged as operator approval)")
        return {"step": 7, "name": "APPROVE", "status": "approved", "mode": "pre-approved"}

    if not sys.stdin.isatty():
        print("\n  BLOCKED: no interactive terminal and no --yes. Refusing to execute.")
        return {"step": 7, "name": "APPROVE", "status": "blocked", "mode": "no-tty"}

    try:
        answer = input("\n  Hospital 70 L first, pump 30 L. Approve dispatch? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  BLOCKED: operator input closed. Refusing to execute.")
        return {"step": 7, "name": "APPROVE", "status": "blocked", "mode": "eof"}

    if answer in ("y", "yes"):
        return {"step": 7, "name": "APPROVE", "status": "approved", "mode": "operator"}

    print("  DENIED by operator. Nothing dispatched.")
    return {"step": 7, "name": "APPROVE", "status": "denied", "mode": "operator"}


def step_replan(town: dict, scenario: str) -> dict:
    """Step 8: a new constraint arrives and the plan must move without a restart."""
    if scenario == "pump-critical":
        # A human insists the pump outranks the hospital. The validator refuses.
        forced = {"hospital": 60, "water_pump": 40}
        rejected = allocator.validate_proposal(forced, town)
        corrected = allocator.policy_solve(town)
        return {
            "step": 8,
            "name": "REPLAN",
            "status": "guardrail_held",
            "instruction": forced,
            "validator_rejected_because": rejected,
            "applied_instead": corrected,
            "note": "the agent will not starve the heart because a human shouted louder",
        }

    if scenario == "reserve-loss":
        # The depot is damaged: only 80 L survive. The heart is still protected.
        damaged = copy.deepcopy(town)
        damaged["reserve"]["total_litres"] = 80
        replanned = allocator.allocate(damaged, mode="policy")
        pump_lph = town["organs"]["water_pump"]["fuel_l_per_hour"]
        before = town["organs"]["water_pump"]["fuel_demand_litres"]
        after = replanned["allocation"].get("water_pump", 0)
        return {
            "step": 8,
            "name": "REPLAN",
            "status": "replanned",
            "trigger": "depot integrity failure, 80 L usable instead of 100 L",
            "allocation": replanned["allocation"],
            "hospital_protected": replanned["allocation"].get("hospital") == 70,
            "pump_hours_before": round(before / pump_lph, 1),
            "pump_hours_after": round(after / pump_lph, 1),
            "water_litres_lost": round(
                (before - after) / pump_lph * town["organs"]["water_pump"]["delivers_litres_per_hour"]
            ),
            "evidence": "recomputed by the same solver and validator, no model call",
        }

    return {"step": 8, "name": "REPLAN", "status": "no_change", "detail": "no new constraint"}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def run(mode: str = "auto", approve: bool = False, scenario: str = "none", log_credit: bool = False) -> dict:
    allocator.load_env()
    town = allocator.load_town()
    started = time.time()

    print(_lifegrid(town))

    steps: list[dict] = []
    for fn in (step_perceive, step_listen, step_graph, step_route):
        result = fn(town)
        steps.append(result)
        _print_step(result, town)

    allocation = step_allocate(town, mode, log_credit)
    steps.append(allocation)
    _print_step(allocation, town)

    budget = step_budget(town)
    steps.append(budget)
    _print_step(budget, town)

    _rule("STEP 7 - HUMAN APPROVAL GATE")
    approval = step_approve(allocation, town, approve)
    steps.append(approval)
    if approval["status"] != "approved":
        run_record = _record(town, steps, scenario, started, executed=False)
        print("\n  Run stopped at the approval gate. Nothing was dispatched.")
        return run_record

    replan = step_replan(town, scenario)
    steps.append(replan)
    _print_step(replan, town)

    return _record(town, steps, scenario, started, executed=True)


def _print_step(result: dict, town: dict) -> None:
    _rule(f"STEP {result['step']} - {result['name']}  [{result.get('status')}]")

    if result["name"] == "PERCEIVE":
        if result["status"] == "pending_capture":
            print(f"  {result['detail']}")
        else:
            print(f"  frames: {result['frames']}  water severity %: {result['water_severity_percent']}")
    elif result["name"] == "LISTEN":
        if result["status"] == "pending_capture":
            print(f"  {result['detail']}")
        else:
            print(f"  reports: {result['reports']}  blocked-road mentions: {result['blocked_mentions']}")
            print(f"  first: {result['sample']}")
    elif result["name"] == "GRAPH":
        print("  fuel -> heart -> lungs -> organs")
        print("  order:", " -> ".join(result["order"]))
        print(f"  if the heart dies: {', '.join(result['if_hospital_fails'])} "
              f"({result['people_affected']} people lose service)")
    elif result["name"] == "ROUTE":
        print("  path:", " -> ".join(result["path"]))
        print(f"  {result['baseline']['direct_corridor_km']} km direct is blocked; "
              f"{result['distance_km']} km found by A*")
        print(f"  saved {result['saving']['km']} km = {result['saving']['percent']}% of the run, "
              f"{result['saving']['fuel_litres']} L diesel")
    elif result["name"] == "ALLOCATE":
        for organ, litres in result["allocation"].items():
            print(f"  {litres:3d} L  {organ:12s} {town['organs'][organ]['role']}")
        print(f"  {result['total']:3d} L  total  (source: {result['source']})")
        print(f"  justification: {result['justification']}")
        if result["trace"].get("rejected"):
            print(f"  model proposal rejected: {result['trace']['rejected']['reasons']}")
    elif result["name"] == "BUDGET":
        print(f"  ${result['spent_usd']:.2f} spent of ${credit_tracker.BUDGET_USD:.0f} plan "
              f"({result['percent_used']:.1f}%), level {result['level'].upper()}")
        for alert in result["alerts"]:
            print(f"  ! {alert}")
    elif result["name"] == "REPLAN":
        if result["status"] == "guardrail_held":
            print(f"  human instruction {result['instruction']} rejected:")
            for reason in result["validator_rejected_because"]:
                print(f"    - {reason}")
            print(f"  applied instead: {result['applied_instead']}")
        elif result["status"] == "replanned":
            print(f"  trigger: {result['trigger']}")
            print(f"  allocation: {result['allocation']}")
            print(f"  hospital still at 70 L: {result['hospital_protected']}")
            print(f"  pump runtime {result['pump_hours_before']} h -> {result['pump_hours_after']} h, "
                  f"{result['water_litres_lost']} L of water lost")
        else:
            print(f"  {result.get('detail')}")


def _record(town: dict, steps: list[dict], scenario: str, started: float, executed: bool) -> dict:
    base = town["baseline"]
    record = {
        "schema": "lifeline.run/1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "town": {"name": town["town"]["name"], "lat": town["town"]["lat"], "lon": town["town"]["lon"]},
        "scenario": scenario,
        "duration_s": round(time.time() - started, 2),
        "executed": executed,
        "steps": steps,
        "measured_outcome": {
            "pump_uptime_minutes": {
                "without_agent": base["without_agent"]["pump_uptime_minutes"],
                "with_agent": base["with_agent"]["pump_uptime_minutes"],
            },
            "fuel_saved_percent": base["with_agent"]["fuel_saved_percent"],
            "water_delivered_after_hours": {
                "without_agent": base["without_agent"]["water_delivered_after_hours"],
                "with_agent": base["with_agent"]["water_delivered_after_hours"],
            },
            "metric_definition": base["metric_definition"],
        },
        "autonomy": {
            "steps_without_human": 6,
            "human_touchpoints": 1,
            "model_calls_required_for_deterministic_steps": 0,
        },
    }
    RUNS.mkdir(exist_ok=True)
    (RUNS / "latest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"\n  run saved to {(RUNS / 'latest.json').relative_to(ROOT)}")
    return record


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="LIFELINE AI - 8 step survival agent")
    parser.add_argument("--yes", action="store_true", help="pre-approve dispatch (recording mode)")
    parser.add_argument("--mode", choices=["auto", "policy", "wonder"], default="auto")
    parser.add_argument("--scenario", choices=["none", "pump-critical", "reserve-loss"], default="none")
    parser.add_argument("--log-credit", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    record = run(mode=args.mode, approve=args.yes, scenario=args.scenario, log_credit=args.log_credit)

    if args.json:
        print(json.dumps(record, indent=2))

    if not record["executed"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
