"""LIFELINE AI - one export, so the UI never hardcodes a number.

    python export_ui_data.py

Reads the real artefacts and writes ui/public/data/lifeline.json:

    town.json                  organs, dependency edges
    dependency_graph.py        Kahn order, cascade blast radius
    a_star.py                  the 7.8 km route and the measured saving
    allocator.py               the 70/30 solution and the evidence chain
    credit_tracker.py          real spend, per model, sub-cent included
    sam_flood_segments.json    measured mask severity per frame
    voice_reports.json         the real transcript
    escalation.py              the four tier windows
    world.py                   the configured points

Also copies the media the page plays: mask overlays, the two videos, the six
Figma frames. If a source file is missing the export says so instead of
inventing a placeholder value.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import a_star
import allocator
import blood
import credit_tracker
import dependency_graph
import escalation
import i18n
import protocols

ROOT = Path(__file__).parent
UI = ROOT / "ui"
PUBLIC = UI / "public"
DATA = PUBLIC / "data"
MEDIA = PUBLIC / "media"
VIDEOS = PUBLIC / "videos"

BASELINE_NOTE = (
    "The 90 min manual baseline is a documented assumption in the README, not a "
    "measured field trial. The 30 min agent figure times the eight steps above."
)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def build() -> dict:
    town = allocator.load_town()
    _, nodes, edges = a_star.load_network()
    route = a_star.plan_route(town, nodes, edges)
    allocation = allocator.allocate(town, mode="policy")

    sam = _read(ROOT / "artifacts" / "sam_flood_segments.json")
    voice = _read(ROOT / "artifacts" / "voice_reports.json")
    credit = credit_tracker.CreditTracker().status()

    frames = []
    if sam:
        for frame in sorted(sam["frames"], key=lambda f: -f["water_severity_percent"]):
            stem = Path(frame["file"]).stem
            have_overlay = (ROOT / "artifacts" / "photos" / "overlays" / f"{stem}.png").exists()
            frames.append({
                "file": frame["file"],
                "stem": stem,
                "severity": frame["water_severity_percent"],
                "objects": len(frame.get("objects", [])),
                "overlay": f"/media/overlays/{stem}.png" if have_overlay else None,
                "photo": f"/media/photos/{frame['file']}" if (ROOT / "artifacts" / "photos" / frame["file"]).exists() else None,
            })

    blast = dependency_graph.cascade(town, ["hospital"])
    order = dependency_graph.kahn_order(town)

    return {
        "generated_from": "live artefacts - re-run python export_ui_data.py",
        "town": town,
        "organs": {
            name: {
                "label": node.get("label"),
                "role": node.get("role"),
                "priority": node.get("priority"),
                "litres": node.get("fuel_litres", node.get("fuel_demand_litres")),
                "runtime_hours": node.get("runtime_hours_left"),
                "people": node.get("people"),
                "lat": node.get("lat"),
                "lon": node.get("lon"),
            }
            for name, node in town["organs"].items()
        },
        "graph": {
            "order": order,
            "edges": [[a, b] for a, b in _edges(town)],
            "cascade": {"if_failed": "hospital", **blast},
        },
        "route": route,
        "protocols": protocols.build(nodes, edges),
        "blood": blood.build(town),
        "allocation": {
            "policy": allocation["allocation"],
            "total": allocation["total"],
            "confidence": allocation["confidence"],
            "source": allocation["source"],
            "justification": allocation["justification"],
            "evidence": allocation["evidence"],
            "inference": allocation.get("inference", []),
            "validation": allocation.get("validation", {}),
        },
        "openweight": _openweight(),
        "sam": {            "available": bool(sam),
            "model": sam.get("model") if sam else None,
            "prompt": sam.get("prompt") if sam else None,
            "frames": frames,
            "worst": frames[0]["severity"] if frames else None,
            "cost_usd": sam.get("cost_usd") if sam else None,
        },
        "voice": {
            "available": bool(voice),
            "model": voice.get("model") if voice else None,
            "transcript": voice["reports"][0]["transcript"] if voice and voice.get("reports") else None,
            "seconds": voice.get("audio_seconds") if voice else None,
            "synthetic": voice["reports"][0].get("synthetic", True) if voice and voice.get("reports") else True,
            "cost_usd": voice.get("cost_usd") if voice else None,
        },
        "credit": {
            "budget_usd": credit["budget_usd"],
            "spent_usd": credit["spent_usd"],
            "percent": credit["percent_used"],
            "level": credit["level"],
            "remaining_usd": credit["remaining_usd"],
            "reserve_usd": credit["reserve_buffer_usd"],
            "by_model": {
                model: bucket for model, bucket in credit["by_model"].items()
                if bucket["calls"] > 0
            },
        },
        "escalation": {
            "tiers": [
                {"tier": 1, "window": "0-5 min", "action": "human gate",
                 "detail": "nothing is dispatched until a person decides"},
                {"tier": 2, "window": "5-15 min", "action": "escalate",
                 "detail": "SMS, WhatsApp and voice payloads in 8 languages, PENDING_CREDENTIALS"},
                {"tier": 3, "window": "15-30 min", "action": "degraded autopilot",
                 "detail": "50 L hospital, 20 L pump, 30 L reserve held"},
                {"tier": 4, "window": "over 30 min", "action": "community consensus",
                 "detail": "3 shelter leaders, 2 of 3 must agree"},
            ],
            "degraded": escalation.degraded_allocation(town),
        },
        "world": {
            "towns": _world(),
            "note": (
                "Coordinates are real. Only Kottur has a surveyed fuel scenario; every "
                "other point returns the labelled generic template, never an invented "
                "local litre count."
            ),
        },
        "locales": [
            {"code": e["code"], "native": e["native"], "language": e["language"], "dir": e["dir"]}
            for e in i18n.available()
        ],
        "messages": {e["code"]: i18n.load(e["code"]) for e in i18n.available()},
        "baseline": {
            "manual_minutes": 90,
            "agent_minutes": 30,
            "note": BASELINE_NOTE,
        },
    }


def _openweight() -> dict:
    """The Baseten proof, read from the artefact - never asserted in the page."""
    path = ROOT / "artifacts" / "openweight_proof.json"
    if not path.exists():
        return {"available": False, "runs": 0, "valid_runs": 0,
                "note": "no proof on file - run python openweight.py"}

    data = json.loads(path.read_text(encoding="utf-8"))
    valid = [run for run in data.get("runs", []) if run.get("valid")]
    return {
        "available": bool(valid),
        "provider": data.get("provider"),
        "model": data.get("model"),
        "runs": len(data.get("runs", [])),
        "valid_runs": len(valid),
        "allocation": valid[-1]["allocation"] if valid else None,
        "latencies_s": [run["latency_s"] for run in valid],
        "latest_at": valid[-1]["at"] if valid else None,
        "note": data.get("note"),
    }


def _edges(town: dict):
    for name, node in town["organs"].items():
        for parent in node.get("depends_on", []):
            yield parent, name


def _world():
    import world
    out = []
    for town in world.WORLD_TOWNS:
        out.append({
            "id": town["id"], "name": town["name"], "country": town["country"],
            "region": town["region"], "lat": town["lat"], "lon": town["lon"],
            "data_class": town["data_class"],
        })
    return out


def _copy_media() -> dict[str, int]:
    counts = {"overlays": 0, "photos": 0, "videos": 0, "figma": 0}
    MEDIA.mkdir(parents=True, exist_ok=True)
    VIDEOS.mkdir(parents=True, exist_ok=True)

    src = ROOT / "artifacts" / "photos" / "overlays"
    if src.exists():
        dst = MEDIA / "overlays"
        dst.mkdir(parents=True, exist_ok=True)
        for png in src.glob("*.png"):
            shutil.copy2(png, dst / png.name)
            counts["overlays"] += 1

    src = ROOT / "artifacts" / "photos"
    if src.exists():
        dst = MEDIA / "photos"
        dst.mkdir(parents=True, exist_ok=True)
        for jpg in src.glob("*.jpg"):
            shutil.copy2(jpg, dst / jpg.name)
            counts["photos"] += 1
        credits = src / "CREDITS.json"
        if credits.exists():
            shutil.copy2(credits, MEDIA / "CREDITS.json")

    for name in ("flood.mp4", "fuel_flow.mp4"):
        src_video = ROOT / "artifacts" / "videos" / name
        if src_video.exists():
            shutil.copy2(src_video, VIDEOS / name)
            counts["videos"] += 1
        else:
            print(f"  missing {src_video} - run python make_video.py", file=sys.stderr)

    src = ROOT / "figma"
    if src.exists():
        dst = MEDIA / "figma"
        dst.mkdir(parents=True, exist_ok=True)
        for png in src.glob("*.png"):
            shutil.copy2(png, dst / png.name)
            counts["figma"] += 1
    return counts


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    DATA.mkdir(parents=True, exist_ok=True)

    payload = build()
    (DATA / "lifeline.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    counts = _copy_media()

    print(f"wrote {DATA / 'lifeline.json'}")
    print(f"  organs         {len(payload['organs'])}")
    print(f"  Kahn order     {' -> '.join(payload['graph']['order'])}")
    print(f"  route          {payload['route']['distance_km']} km, "
          f"{payload['route']['saving']['percent']}% saved")
    print(f"  allocation     {payload['allocation']['policy']} = {payload['allocation']['total']} L")
    print(f"  sam frames     {len(payload['sam']['frames'])} (worst {payload['sam']['worst']}%)")
    print(f"  voice          {'present' if payload['voice']['available'] else 'missing'}")
    print(f"  credit         ${payload['credit']['spent_usd']:.6f} of "
          f"${payload['credit']['budget_usd']:.0f}")
    print(f"  locales        {len(payload['locales'])}")
    print(f"  media          {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
