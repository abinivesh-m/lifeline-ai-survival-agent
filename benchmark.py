"""Measure the parts that decide the demo, on this machine, right now.

Nothing here is a marketing number: every row is a loop this script ran. Model
latencies are read from the artefacts those calls produced (a recorded value,
not a re-estimate), and the local timings are re-measured every run.

    python benchmark.py                 # write artifacts/benchmark.json
    python benchmark.py --repeat 2000   # longer local loops
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import a_star
import allocator
import credit_tracker
import dependency_graph
import escalation
import i18n

ROOT = Path(__file__).parent
OUT = ROOT / "artifacts" / "benchmark.json"


def _time(fn, repeat: int) -> dict:
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1000.0)
    samples.sort()
    return {
        "repeat": repeat,
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(samples[int(len(samples) * 0.95) - 1], 3),
        "min_ms": round(samples[0], 3),
        "max_ms": round(samples[-1], 3),
    }


def _read(name: str) -> dict | None:
    path = ROOT / "artifacts" / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def recorded() -> dict:
    """Latencies other steps already paid for, read back from their artefacts."""
    out: dict = {}

    run = _read("openweight_proof.json") or {}
    valid = [r for r in run.get("runs", []) if r.get("valid")]
    if valid:
        out["openweight_brain"] = {
            "model": valid[0].get("model") or "meta-models/muse-spark-open-1026",
            "latencies_s": [round(r["latency_s"], 2) for r in valid if r.get("latency_s")],
            "source": "artifacts/openweight_proof.json",
        }

    voice = _read("voice_reports.json") or {}
    reports = voice.get("reports") or []
    if reports:
        out["asr"] = {
            "model": voice.get("model"),
            "audio_seconds": voice.get("audio_seconds"),
            "source": "artifacts/voice_reports.json",
        }

    synth = _read("voice_synth.json") or {}
    clips = synth.get("clips") or []
    if clips:
        rtf = [c["synth_s"] / c["seconds"] for c in clips if c.get("seconds")]
        out["tts"] = {
            "engine": synth.get("engine", {}).get("name"),
            "device": synth.get("engine", {}).get("device"),
            "clips": len(clips),
            "audio_seconds": round(sum(c["seconds"] for c in clips), 2),
            "synth_seconds": round(sum(c["synth_s"] for c in clips), 2),
            "real_time_factor": round(statistics.median(rtf), 3) if rtf else None,
            "source": "artifacts/voice_synth.json",
        }

    multi = _read("multilingual_payloads.json") or {}
    locales = multi.get("locales") or []
    draft = [r["draft"]["latency_s"] for r in locales if r.get("draft")]
    review = [r["review"]["latency_s"] for r in locales if (r.get("review") or {}).get("latency_s")]
    if draft or review:
        out["drafting"] = {
            "model": multi.get("generator", {}).get("model"),
            "reviewer": multi.get("reviewer", {}).get("model"),
            "locales": len(locales),
            "draft_s": draft,
            "review_s": review,
            "source": "artifacts/multilingual_payloads.json",
        }
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Local benchmark + recorded model latencies")
    parser.add_argument("--repeat", type=int, default=500)
    args = parser.parse_args(argv)

    town, nodes, edges = a_star.load_network()

    local = {
        "route_a_star": _time(lambda: a_star.plan_route(town, nodes, edges), args.repeat),
        "topological_order": _time(lambda: dependency_graph.kahn_order(town), args.repeat * 4),
        "allocate_policy": _time(lambda: allocator.allocate(town, mode="policy"), args.repeat * 2),
        "validate_allocation": _time(
            lambda: allocator.validate_proposal(
                {"allocation": {"hospital": 70, "water_pump": 30}, "total": 100}, town
            ),
            args.repeat * 2,
        ),
        "escalation_8_locales": _time(
            lambda: [escalation.notifications(2, town, locale=e["code"]) for e in i18n.available()],
            max(20, args.repeat // 10),
        ),
    }

    ledger = credit_tracker.CreditTracker()
    payload = {
        "schema": "lifeline.benchmark/1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu": platform.processor() or platform.machine(),
            "cpu_count": __import__("os").cpu_count(),
        },
        "local": local,
        "recorded": recorded(),
        "ledger": {
            "spent_usd": ledger.spend_precise(),
            "rows": len(ledger.entries),
            "calls": ledger.calls(),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"  machine  {payload['machine']['platform']} · {payload['machine']['python']}")
    print(f"  {'step':26s} {'median':>9s} {'p95':>9s}  (ms, {args.repeat} loops)")
    for name, row in local.items():
        print(f"  {name:26s} {row['median_ms']:9.3f} {row['p95_ms']:9.3f}")
    rec = payload["recorded"]
    if "openweight_brain" in rec:
        print(f"  brain    recorded {rec['openweight_brain']['latencies_s']} s")
    if "tts" in rec:
        print(
            f"  tts      {rec['tts']['audio_seconds']}s audio in {rec['tts']['synth_seconds']}s "
            f"· RTF {rec['tts']['real_time_factor']}"
        )
    if "drafting" in rec:
        print(f"  drafting {len(rec['drafting']['draft_s'])} locales recorded")
    print(f"  graph    {len(dependency_graph.kahn_order(town))} nodes · wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
