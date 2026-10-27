"""LIFELINE AI - the Open Weight qualifying path, actually executed.

The $10,000 Open Weight prize requires a Meta open-weight model served on the
participant's own hardware or through partner inference. This repo cannot run
Muse Glimmer on a 6 GB laptop, so the qualifying path is the partner one:

    meta-models/muse-spark-open-1026  on Baseten

This script makes that call for real, validates the answer with the same
arithmetic the local solver uses, and appends the whole exchange - request,
response text, token usage, latency - to artifacts/openweight_proof.json.

What it is NOT: the local llama3.2:3b run. That proves the deterministic core
works with the network off, and it is labelled as such everywhere. It does not
qualify for Open Weight and this repo never says it does.

Run:
    python openweight.py
    python openweight.py --verify
    python openweight.py --cases 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import allocator

ROOT = Path(__file__).parent
PROOF_PATH = ROOT / "artifacts" / "openweight_proof.json"

PROVIDER = "Baseten"
# The hackathon docs are explicit: use the -1026 suffix, not the generic alias.
REQUIRED_MODEL = "meta-models/muse-spark-open-1026"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prompt(town: dict) -> str:
    reserve = town["reserve"]["total_litres"]
    hospital = town["organs"]["hospital"]
    pump = town["organs"]["water_pump"]
    shelters = town["organs"]["shelters"]
    return (
        "You are the allocation step of a disaster fuel agent. Diesel only. "
        "Never give medical advice, never triage patients, never mention medicine.\n\n"
        f"Reserve at the depot: {reserve} L.\n"
        f"Hospital (heart, priority 1): needs up to {hospital['fuel_demand_litres']} L, "
        f"burns {hospital['generator_l_per_hour']} L/h, {hospital['runtime_hours_left']} h left.\n"
        f"Water pump (lungs, priority 2): needs up to {pump['fuel_demand_litres']} L, "
        f"burns {pump['fuel_l_per_hour']} L/h, and only runs if the hospital feeder has power.\n"
        f"Shelters (organs, priority 3): {shelters['people']} people, no water.\n"
        f"Road: the 4.2 km direct corridor is blocked; the A* detour is 7.8 km.\n\n"
        "Hard constraints: the two allocations must sum to exactly the reserve; never "
        "exceed a stated demand; do not fund a lower priority while a higher one starves.\n\n"
        'Reply with JSON only: {"allocation": {"hospital": <L>, "water_pump": <L>}, '
        '"justification": "<one sentence>", "confidence": <0-1>}'
    )


def validate(allocation: dict, town: dict) -> tuple[bool, list[str]]:
    problems: list[str] = []
    reserve = town["reserve"]["total_litres"]
    caps = {
        "hospital": town["organs"]["hospital"]["fuel_demand_litres"],
        "water_pump": town["organs"]["water_pump"]["fuel_demand_litres"],
    }
    if set(allocation) != set(caps):
        problems.append(f"keys must be exactly {sorted(caps)}")
        return False, problems
    for key, cap in caps.items():
        value = allocation[key]
        if not isinstance(value, (int, float)):
            problems.append(f"{key} is not a number")
        elif value < 0:
            problems.append(f"{key} is negative")
        elif value > cap:
            problems.append(f"{key} exceeds its {cap} L demand")
    if not problems and sum(allocation.values()) != reserve:
        problems.append(f"total {sum(allocation.values())} L != reserve {reserve} L")
    if not problems and allocation["hospital"] < allocation["water_pump"]:
        problems.append("lower priority funded above the heart")
    return not problems, problems


def call(prompt: str, timeout: float = 90.0) -> dict:
    base = os.environ.get("BASETEN_BASE_URL", "").rstrip("/")
    key = os.environ.get("BASETEN_API_KEY", "")
    model = os.environ.get("BASETEN_MODEL", REQUIRED_MODEL)

    if not base or not key:
        raise RuntimeError("BASETEN_BASE_URL and BASETEN_API_KEY must be set in .env")
    if model != REQUIRED_MODEL:
        raise RuntimeError(
            f"BASETEN_MODEL is {model}; the hackathon requires {REQUIRED_MODEL}"
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        # Muse Spark Open is a reasoning model: reasoning tokens bill against
        # max_tokens. A 600-token cap produced finish_reason=length and null
        # content, with 2651 characters of reasoning and no answer. 3000 leaves
        # room for the trace plus the JSON.
        "max_tokens": int(os.environ.get("BASETEN_MAX_TOKENS", "3000")),
    }
    request = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )

    started = time.time()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    latency = time.time() - started

    choice = body["choices"][0]
    message = choice.get("message", {})
    text = message.get("content")
    reasoning = message.get("reasoning_content") or ""

    if not text:
        raise RuntimeError(
            "empty content: finish_reason="
            f"{choice.get('finish_reason')}, reasoning_chars={len(reasoning)} - "
            "raise BASETEN_MAX_TOKENS"
        )

    return {
        "latency_s": round(latency, 2),
        "response_text": text,
        "reasoning_chars": len(reasoning),
        "reasoning_preview": reasoning[:600] or None,
        "finish_reason": choice.get("finish_reason"),
        "usage": body.get("usage", {}),
        "model_served": body.get("model", model),
        "request_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }


def parse(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned[4:] if cleaned.startswith("json") else cleaned
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None


def load_proof() -> dict:
    if PROOF_PATH.exists():
        return json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    return {
        "provider": PROVIDER,
        "model": REQUIRED_MODEL,
        "role": "Open Weight qualifying path - partner-hosted Meta open weights",
        "note": (
            "Every run below is a real HTTP request whose response text is stored "
            "verbatim. Validation is recomputed locally, never trusted from the model."
        ),
        "runs": [],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="run Muse Spark Open on Baseten")
    parser.add_argument("--cases", type=int, default=1, help="how many runs to make")
    parser.add_argument("--verify", action="store_true", help="print the stored proof")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.verify:
        proof = load_proof()
        valid = [r for r in proof["runs"] if r.get("valid")]
        summary = {
            "provider": proof["provider"],
            "model": proof["model"],
            "runs": len(proof["runs"]),
            "valid_runs": len(valid),
            "ok": bool(valid),
            "latest": valid[-1]["at"] if valid else None,
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f'{proof["provider"]} · {proof["model"]}')
            print(f'  runs {summary["runs"]}, valid {summary["valid_runs"]}')
            for run in proof["runs"]:
                mark = "PASS" if run.get("valid") else "FAIL"
                if run.get("valid"):
                    print(f'  {run["at"]}  {mark}  {run["allocation"]}  {run["latency_s"]}s')
                else:
                    print(f'  {run["at"]}  {mark}  {run.get("error", "invalid")[:90]}')
            if not valid:
                print("  no valid run on record - run: python openweight.py")
        return 0 if valid else 1

    allocator.load_env()
    town = allocator.load_town()
    prompt = _prompt(town)
    proof = load_proof()

    for index in range(args.cases):
        record: dict = {"at": _now(), "provider": PROVIDER, "model": REQUIRED_MODEL}
        try:
            result = call(prompt)
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
            record.update({"valid": False, "error": str(exc)[:400]})
            proof["runs"].append(record)
            print(f"run {index + 1}: ERROR {exc}")
            continue

        record.update(result)
        parsed = parse(result["response_text"]) or {}
        allocation = parsed.get("allocation", {})
        valid, problems = validate(allocation, town)
        record.update({
            "allocation": allocation,
            "justification": parsed.get("justification"),
            "confidence": parsed.get("confidence"),
            "valid": valid,
            "problems": problems,
        })
        proof["runs"].append(record)
        print(f'run {index + 1}: {"PASS" if valid else "FAIL"}  {allocation}  '
              f'{result["latency_s"]}s  tokens {result["usage"].get("total_tokens", "?")}')
        if problems:
            print(f'  problems: {problems}')

    PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROOF_PATH.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {PROOF_PATH}")
    return 0 if any(r.get("valid") for r in proof["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

