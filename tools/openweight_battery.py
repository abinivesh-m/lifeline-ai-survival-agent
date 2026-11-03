"""Exercise Muse Spark Open across varied scarcity scenarios.

The original proof was four runs from two distinct prompts, which reads as one
scenario repeated. This battery puts the same model through six different
reserve/demand shapes, stores every exchange verbatim, and re-validates each
answer locally with openweight.validate() - including one deliberately
impossible case, so the validator's teeth are on the record too.

    python tools/openweight_battery.py

Appends to artifacts/openweight_proof.json. Never rewrites existing runs.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import allocator  # noqa: E402
import openweight  # noqa: E402

# name, reserve L, hospital demand L, pump demand L, expectation
SCENARIOS = [
    ("base-100L", 100, 70, 30, "valid"),
    ("scarce-60L", 60, 70, 30, "valid"),
    ("pump-heavy-100L", 100, 40, 60, "rejected"),
    ("hospital-heavy-90L", 90, 80, 20, "valid"),
    ("tight-30L", 30, 20, 15, "valid"),
    ("impossible-120L", 120, 70, 30, "rejected"),
]

# pump-heavy-100L is expected to be refused: the model can satisfy both caps and
# the exact sum, yet still invert priority (pump 60 L > heart 40 L), and
# validate() will not accept that. The first live run did exactly this, so the
# stored record is labelled "rejected" with a note.
NOTES = {
    "pump-heavy-100L": (
        "Both demand caps met and the split summed to the reserve, but the lower "
        "priority received more than the heart. validate() refuses that by design."
    ),
    "impossible-120L": (
        "Demand caps total 100 L against a 120 L reserve, so no split can satisfy "
        "the hard constraint. The model answered anyway; the validator rejected it."
    ),
}


def scenario_town(base: dict, reserve: int, hospital: int, pump: int) -> dict:
    town = copy.deepcopy(base)
    town["reserve"]["total_litres"] = reserve
    town["organs"]["hospital"]["fuel_demand_litres"] = hospital
    town["organs"]["water_pump"]["fuel_demand_litres"] = pump
    return town


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    allocator.load_env()
    base = allocator.load_town()
    proof = openweight.load_proof()
    before = len(proof["runs"])

    rows = []
    for name, reserve, hospital, pump, expectation in SCENARIOS:
        town = scenario_town(base, reserve, hospital, pump)
        prompt = openweight._prompt(town)
        record = {
            "at": openweight._now(),
            "scenario": name,
            "expectation": expectation,
            "provider": openweight.PROVIDER,
            "model": openweight.REQUIRED_MODEL,
            "reserve_litres": reserve,
            "demands": {"hospital": hospital, "water_pump": pump},
        }
        if name in NOTES:
            record["note"] = NOTES[name]
        try:
            result = openweight.call(prompt)
        except Exception as exc:  # noqa: BLE001 - recorded, never crashed silently
            record.update({"valid": False, "error": f"{type(exc).__name__}: {exc}"[:400],
                           "matches_expectation": False})
            proof["runs"].append(record)
            rows.append((name, "ERROR", str(exc)[:70], False))
            continue

        record.update(result)
        parsed = openweight.parse(result["response_text"]) or {}
        allocation = parsed.get("allocation", {})
        valid, problems = openweight.validate(allocation, town)
        matches = (valid and expectation == "valid") or (not valid and expectation == "rejected")
        record.update({
            "allocation": allocation,
            "justification": parsed.get("justification"),
            "confidence": parsed.get("confidence"),
            "valid": valid,
            "problems": problems,
            "matches_expectation": matches,
        })
        proof["runs"].append(record)
        rows.append((name, "PASS" if valid else "REJECTED", str(allocation), matches))

    openweight.PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    openweight.PROOF_PATH.write_text(
        json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{'scenario':22} {'result':9} {'allocation':28} matches")
    print("-" * 74)
    for name, status, allocation, matches in rows:
        print(f"{name:22} {status:9} {allocation:28} {'yes' if matches else 'NO'}")

    added = proof["runs"][before:]
    ok = sum(1 for r in added if r.get("matches_expectation"))
    print(f"\n{ok}/{len(added)} matched the expected outcome")
    print(f"total runs on record: {len(proof['runs'])} -> {openweight.PROOF_PATH}")
    return 0 if ok == len(added) else 1


if __name__ == "__main__":
    raise SystemExit(main())
