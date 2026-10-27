"""LIFELINE AI - exact diesel allocation with evidence / inference separation.

The rule is not "ask a model what to do".  It is:

  1. EVIDENCE  - facts copied out of town.json with their source path.
  2. INFERENCE - the allocation decision, each claim bound to evidence ids.
  3. SOLVER    - a deterministic priority waterfall that can only distribute
                 the real reserve, never more than a node's stated demand.
  4. VALIDATOR - code checks the proposal (model or policy) against hard
                 constraints: 100 L total, 70 L hospital cap, 30 L pump cap,
                 and no funding a low-priority organ while a higher one starves.

If Wonder is configured it proposes the allocation and the validator either
accepts it or rejects it with reasons and the deterministic solver takes over.
The model never executes anything: a human approval gate sits after this step.

Result for the Kottur crisis: 70 L hospital + 30 L pump = exactly 100 L.

Run:  python allocator.py
      python allocator.py --mode policy --json
      python allocator.py --mode wonder --log-credit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

TOWN_PATH = Path(__file__).with_name("town.json")
ENV_PATH = Path(__file__).with_name(".env")


class AllocationError(ValueError):
    """Raised when a proposal breaks a hard allocation constraint."""


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

def load_env(path: str | Path = ENV_PATH) -> None:
    """Minimal .env loader so the core needs no third-party dependency."""
    path = Path(path)
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_town(path: str | Path | None = None) -> dict:
    path = Path(path) if path else TOWN_PATH
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# step 1 - evidence
# --------------------------------------------------------------------------- #

def build_evidence(town: dict) -> list[dict[str, Any]]:
    """Facts only. Every item carries the exact field it came from."""
    organs = town["organs"]
    hospital = organs["hospital"]
    pump = organs["water_pump"]
    shelters = organs["shelters"]

    return [
        {
            "id": "E1",
            "claim": "hospital generator has 4 h of runtime left",
            "value": hospital["runtime_hours_left"],
            "unit": "h",
            "source": "town.json#organs.hospital.runtime_hours_left",
        },
        {
            "id": "E2",
            "claim": "hospital needs 70 L of diesel to cover the 6 h road closure",
            "value": hospital["fuel_demand_litres"],
            "unit": "L",
            "source": "town.json#organs.hospital.fuel_demand_litres",
        },
        {
            "id": "E3",
            "claim": "water pump needs 30 L to keep pumping through the closure",
            "value": pump["fuel_demand_litres"],
            "unit": "L",
            "source": "town.json#organs.water_pump.fuel_demand_litres",
        },
        {
            "id": "E4",
            "claim": "200 people depend on the hospital feeder",
            "value": hospital["serves_people"],
            "unit": "people",
            "source": "town.json#organs.hospital.serves_people",
        },
        {
            "id": "E5",
            "claim": "200 people in shelters have no water until the pump runs",
            "value": shelters["people"],
            "unit": "people",
            "source": "town.json#organs.shelters.people",
        },
        {
            "id": "E6",
            "claim": "the pump draws power from the hospital feeder, so the heart must be stable first",
            "value": pump["powered_from"],
            "unit": "organ",
            "source": "town.json#organs.water_pump.powered_from",
        },
        {
            "id": "E7",
            "claim": "total diesel reserve at the depot",
            "value": town["reserve"]["total_litres"],
            "unit": "L",
            "source": "town.json#reserve.total_litres",
        },
        {
            "id": "E8",
            "claim": "NH-544 km 42 is blocked for ~6 h",
            "value": town["crisis"]["expected_clear_hours"],
            "unit": "h",
            "source": "town.json#crisis.expected_clear_hours",
        },
    ]


def hard_constraints(town: dict) -> dict[str, Any]:
    organs = town["organs"]
    return {
        "reserve_litres": int(town["reserve"]["total_litres"]),
        "caps_litres": {
            name: int(node["fuel_demand_litres"])
            for name, node in organs.items()
            if "fuel_demand_litres" in node
        },
        "priority_order": list(town["allocation_policy"]["priority_order"]),
        "min_unit_litres": int(town["allocation_policy"]["min_unit_litres"]),
        "fill_reserve_exactly": True,
    }


# --------------------------------------------------------------------------- #
# step 2 - deterministic solver
# --------------------------------------------------------------------------- #

def policy_solve(town: dict) -> dict[str, int]:
    """Priority waterfall: fund the heart, then the lungs, never over demand."""
    constraints = hard_constraints(town)
    remaining = constraints["reserve_litres"]
    allocation: dict[str, int] = {}

    for organ in constraints["priority_order"]:
        cap = constraints["caps_litres"].get(organ, 0)
        give = min(cap, remaining)
        if give > 0:
            allocation[organ] = give
        remaining -= give

    if remaining > 0:
        allocation["unallocated"] = remaining
    return allocation


def validate_proposal(allocation: dict[str, Any], town: dict) -> list[str]:
    """Every hard rule, checked in code. Returns a list of failures."""
    problems: list[str] = []
    constraints = hard_constraints(town)
    caps = constraints["caps_litres"]

    if not isinstance(allocation, dict):
        return ["allocation must be an object of organ -> litres"]

    for organ, litres in allocation.items():
        if organ == "unallocated":
            continue
        if organ not in caps:
            problems.append(f"{organ}: not a diesel-consuming organ in town.json")
            continue
        if not isinstance(litres, (int, float)) or isinstance(litres, bool):
            problems.append(f"{organ}: litres must be a number")
            continue
        if litres < 0:
            problems.append(f"{organ}: negative allocation")
        if litres > caps[organ]:
            problems.append(f"{organ}: {litres} L exceeds stated demand {caps[organ]} L")
        if litres % constraints["min_unit_litres"] != 0:
            problems.append(f"{organ}: {litres} L is not a multiple of {constraints['min_unit_litres']} L")

    total = sum(v for k, v in allocation.items() if k != "unallocated" and isinstance(v, (int, float)))
    if total > constraints["reserve_litres"]:
        problems.append(f"total {total} L exceeds reserve {constraints['reserve_litres']} L")
    if constraints["fill_reserve_exactly"] and total != constraints["reserve_litres"]:
        problems.append(f"total {total} L does not match reserve {constraints['reserve_litres']} L exactly")

    # Starvation rule: never fund a lower-priority organ while a higher one is short.
    for i, organ in enumerate(constraints["priority_order"]):
        if allocation.get(organ, 0) >= caps.get(organ, 0):
            continue
        shorted = [o for o in constraints["priority_order"][i + 1 :] if allocation.get(o, 0) > 0]
        if shorted:
            problems.append(
                f"{organ} is under-funded ({allocation.get(organ, 0)}/{caps.get(organ, 0)} L) "
                f"while {', '.join(shorted)} receives diesel"
            )
            break

    return problems


# --------------------------------------------------------------------------- #
# step 3 - optional Wonder proposal
# --------------------------------------------------------------------------- #

def wonder_configured() -> bool:
    if os.environ.get("LIFELINE_OFFLINE", "0") == "1":
        return False
    return bool(os.environ.get("META_API_KEY") and os.environ.get("META_API_BASE"))


def _prompt(town: dict, evidence: list[dict], constraints: dict) -> str:
    facts = "\n".join(f"  [{e['id']}] {e['claim']} = {e['value']} {e['unit']}" for e in evidence)
    return (
        "You are the allocation reasoner for a flood response in Kottur, Tamil Nadu.\n"
        "A diesel depot holds a fixed reserve and three organs need it. Allocate it.\n\n"
        f"EVIDENCE\n{facts}\n\n"
        "HARD CONSTRAINTS (a validator will reject any breach)\n"
        f"  total must equal exactly {constraints['reserve_litres']} L\n"
        f"  caps: {json.dumps(constraints['caps_litres'])}\n"
        f"  priority order: {', '.join(constraints['priority_order'])}\n"
        f"  each organ gets a multiple of {constraints['min_unit_litres']} L\n"
        "  never give diesel to a lower-priority organ while a higher-priority one is short\n\n"
        "Reply with JSON only, no prose, no code fences:\n"
        '{"allocation": {"hospital": <L>, "water_pump": <L>}, '
        '"justification": "<one sentence>", "confidence": <0-1>}'
    )


def wonder_allocate(town: dict, evidence: list[dict], timeout: float = 60.0) -> tuple[dict | None, dict]:
    """Ask Wonder for a proposal. Returns (proposal, trace); proposal is None on failure."""
    meta = {
        "model": os.environ.get("META_MODEL", "muse-wonder-1.0"),
        "endpoint": os.environ.get("META_API_BASE", ""),
        "reasoning_effort": os.environ.get("META_REASONING_EFFORT", ""),
        "status": "skipped",
        "latency_s": None,
        "raw_preview": None,
    }
    if not wonder_configured():
        meta["status"] = "unconfigured"
        if os.environ.get("LIFELINE_OFFLINE", "0") == "1":
            meta["detail"] = "LIFELINE_OFFLINE=1 - no network calls, deterministic solver only"
        else:
            meta["detail"] = "set META_API_BASE and META_API_KEY in .env to enable live calls"
        return None, meta

    constraints = hard_constraints(town)
    payload = {
        "model": meta["model"],
        "messages": [
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": _prompt(town, evidence, constraints)},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    if meta["reasoning_effort"]:
        # Top-level on Chat Completions; Muse Wonder: minimal|low|medium|high|xhigh|max
        payload["reasoning_effort"] = meta["reasoning_effort"]
    if os.environ.get("META_MAX_TOKENS"):
        payload["max_tokens"] = int(os.environ["META_MAX_TOKENS"])
    request = urllib.request.Request(
        meta["endpoint"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['META_API_KEY']}",
        },
        method="POST",
    )

    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        meta["status"] = "error"
        meta["detail"] = f"{type(exc).__name__}: {exc}"
        return None, meta

    meta["latency_s"] = round(time.time() - started, 2)
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        meta["status"] = "error"
        meta["detail"] = "response did not contain choices[0].message.content"
        return None, meta

    meta["raw_preview"] = content[:400]
    cleaned = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        proposal = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        meta["status"] = "unparseable"
        meta["detail"] = str(exc)
        return None, meta

    meta["status"] = "answered"
    return proposal, meta


# --------------------------------------------------------------------------- #
# step 4 - assemble + validate
# --------------------------------------------------------------------------- #

def allocate(town: dict, mode: str = "auto", log_credit: bool = False) -> dict:
    evidence = build_evidence(town)
    constraints = hard_constraints(town)
    trace: dict[str, Any] = {"requested_mode": mode}
    proposal: dict | None = None
    source = "policy"

    if mode in ("auto", "wonder"):
        candidate, wonder_meta = wonder_allocate(town, evidence)
        trace["wonder"] = wonder_meta
        if candidate is None:
            source = "policy"
        else:
            problems = validate_proposal(candidate.get("allocation", {}), town)
            if problems:
                trace["rejected"] = {
                    "allocation": candidate.get("allocation"),
                    "reasons": problems,
                }
                source = "policy-fallback"
            else:
                proposal = candidate
                source = "wonder-high"
                if log_credit:
                    try:
                        import credit_tracker

                        credit_tracker.CreditTracker().log(
                            "wonder",
                            calls=1,
                            note="allocator allocation proposal (accepted by validator)",
                        )
                    except Exception as exc:  # never let accounting break the response
                        trace["credit_log_error"] = str(exc)

    if proposal is None:
        allocation = policy_solve(town)
        justification = (
            "Heart first, lungs next: the hospital's 4 h of runtime is the nearest failure, "
            "and the pump is fed from the hospital feeder, so 70 L hospital + 30 L pump "
            "is the only split that keeps both alive for the 6 h closure."
        )
        confidence = 0.99
    else:
        allocation = {k: int(v) for k, v in proposal["allocation"].items()}
        justification = str(proposal.get("justification", "")).strip()
        confidence = float(proposal.get("confidence", 0.0))

    problems = validate_proposal(allocation, town)
    if problems:
        # A policy result that fails validation is a bug, not a model failure.
        raise AllocationError("allocation failed validation: " + "; ".join(problems))

    return {
        "allocation": allocation,
        "total": sum(allocation.values()),
        "evidence": evidence,
        "inference": [
            {
                "claim": "fund the hospital first",
                "litres": allocation.get("hospital", 0),
                "because": ["E1", "E2", "E4"],
                "confidence": 0.99,
            },
            {
                "claim": "fund the pump second, inside the hospital feeder budget",
                "litres": allocation.get("water_pump", 0),
                "because": ["E3", "E5", "E6"],
                "confidence": 0.95,
            },
            {
                "claim": "no diesel left over, no organ over-funded",
                "litres": 0,
                "because": ["E7", "E8"],
                "confidence": 1.0,
            },
        ],
        "justification": justification,
        "confidence": confidence,
        "constraints": constraints,
        "validation": {"ok": True, "checks": _checks(town, allocation)},
        "source": source,
        "trace": trace,
        "human_approval_required": True,
        "executed": False,
        "safety": "diesel allocation only - no medical triage, no dosing, no clinical advice",
    }


def _checks(town: dict, allocation: dict[str, int]) -> list[str]:
    constraints = hard_constraints(town)
    return [
        f"total {sum(allocation.values())} L == reserve {constraints['reserve_litres']} L",
        f"hospital {allocation.get('hospital', 0)} L <= cap "
        f"{constraints['caps_litres'].get('hospital', 0)} L",
        f"pump {allocation.get('water_pump', 0)} L <= cap "
        f"{constraints['caps_litres'].get('water_pump', 0)} L",
        "priority order respected (hospital before water_pump)",
        f"units are multiples of {constraints['min_unit_litres']} L",
        "nothing executed - awaiting human approval",
    ]


def _fmt(result: dict, town: dict) -> str:
    org = town["organs"]
    lines = ["ALLOCATION  (source: %s)" % result["source"], ""]
    for name, litres in result["allocation"].items():
        role = org.get(name, {}).get("role", "")
        bar = "#" * max(1, round(litres / 2))
        lines.append(f"  {name:12s} {role:6s} {litres:3d} L  {bar}")
    lines += [
        f"  {'total':12s} {'':6s} {result['total']:3d} L",
        "",
        "EVIDENCE",
    ]
    for item in result["evidence"]:
        lines.append(f"  [{item['id']}] {item['claim']}  <- {item['source']}")
    lines += ["", "INFERENCE"]
    for item in result["inference"]:
        lines.append(
            f"  - {item['claim']} ({item['litres']} L, from {', '.join(item['because'])})"
        )
    lines += [
        "",
        f"JUSTIFICATION: {result['justification']}",
        "",
        "VALIDATION",
    ]
    lines += [f"  ok  {check}" for check in result["validation"]["checks"]]
    if result["trace"].get("rejected"):
        lines.append(f"  model proposal rejected: {result['trace']['rejected']['reasons']}")
    lines += [
        "",
        "HUMAN APPROVAL REQUIRED - nothing has been executed.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    load_env()
    parser = argparse.ArgumentParser(description="LIFELINE AI allocator")
    parser.add_argument("--mode", choices=["auto", "policy", "wonder"], default="auto")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--log-credit", action="store_true")
    parser.add_argument("--town", default=str(TOWN_PATH))
    args = parser.parse_args(argv)

    town = load_town(args.town)
    try:
        result = allocate(town, mode=args.mode, log_credit=args.log_credit)
    except AllocationError as exc:
        print(f"allocation refused: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(_fmt(result, town))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
