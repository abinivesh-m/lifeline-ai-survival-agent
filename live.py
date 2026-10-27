"""LIFELINE AI - live runner. Watch the 8-step agent work in a browser.

    python live.py                # http://127.0.0.1:8765
    python live.py --fresh        # force a new Wonder call instead of the cache
    python live.py --port 8765

No web framework, no build step: http.server + server-sent events. The page
streams one event per step so you can see the agent think, hold at the human
gate, and replan after your decision.

Wonder is cached in artifacts/wonder_last.json so a demo rehearsal does not
burn credit re-asking the same question. Use --fresh to spend one call.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import a_star
import allocator
import credit_tracker
import dependency_graph

ROOT = Path(__file__).parent
UI = ROOT / "live_ui.html"
WONDER_CACHE = ROOT / "artifacts" / "wonder_last.json"

STATE = {"approval": None, "scenario": "reserve-loss"}
APPROVAL_EVENT = threading.Event()
STEP_DELAY = 0.75


def _sam():
    path = ROOT / "artifacts" / "sam_flood_segments.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _voice():
    path = ROOT / "artifacts" / "voice_reports.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _allocate(town: dict, fresh: bool) -> tuple[dict, str]:
    if not fresh and WONDER_CACHE.exists():
        cached = json.loads(WONDER_CACHE.read_text(encoding="utf-8"))
        return cached, "cache"
    result = allocator.allocate(town, mode="auto", log_credit=True)
    WONDER_CACHE.parent.mkdir(exist_ok=True)
    WONDER_CACHE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result, "live"


def pipeline(fresh: bool):
    """Yield one dict per step. Runs in the request thread."""
    allocator.load_env()
    town = allocator.load_town()

    sam = _sam()
    if sam:
        frames = sam["frames"]
        sev = [f["water_severity_percent"] for f in frames]
        worst = max(frames, key=lambda f: f["water_severity_percent"])
        yield {
            "step": 1, "name": "PERCEIVE", "status": "ok", "model": sam["model"],
            "detail": f'{len(frames)} images segmented, prompt "{sam["prompt"]}"',
            "severity": sev, "worst": worst["file"],
            "worst_pct": worst["water_severity_percent"],
            "cost_usd": sam.get("cost_usd"),
        }
    else:
        yield {"step": 1, "name": "PERCEIVE", "status": "pending", "detail": "run capture_sam.py"}

    time.sleep(STEP_DELAY)

    voice = _voice()
    if voice:
        reps = voice["reports"]
        yield {
            "step": 2, "name": "LISTEN", "status": "ok", "model": voice["model"],
            "detail": f"{len(reps)} Tamil report(s), {voice['audio_seconds']}s of audio",
            "transcript": reps[0]["transcript"], "synthetic": reps[0].get("synthetic", False),
            "cost_usd": voice.get("cost_usd"),
        }
    else:
        yield {"step": 2, "name": "LISTEN", "status": "pending", "detail": "run capture_voice.py"}

    time.sleep(STEP_DELAY)

    order = dependency_graph.kahn_order(town)
    blast = dependency_graph.cascade(town, ["hospital"])
    yield {
        "step": 3, "name": "GRAPH", "status": "ok",
        "order": order, "downstream": blast["downstream_failed"],
        "people": blast["people_affected"],
        "detail": "Kahn topological sort - heartbeat first, lungs second",
    }

    time.sleep(STEP_DELAY)

    _, nodes, edges = a_star.load_network()
    route = a_star.plan_route(town, nodes, edges)
    yield {
        "step": 4, "name": "ROUTE", "status": "ok",
        "path": route["path"], "km": route["distance_km"],
        "saving": route["saving"],
        "detail": f'A* found {route["distance_km"]} km vs the blocked 4.2 km corridor',
    }

    time.sleep(STEP_DELAY)

    allocation, source = _allocate(town, fresh)
    yield {
        "step": 5, "name": "ALLOCATE", "status": "ok",
        "allocation": allocation["allocation"], "total": allocation["total"],
        "justification": allocation["justification"],
        "source": allocation["source"], "cache": source,
        "wonder": allocation["trace"].get("wonder", {}),
        "evidence": allocation["evidence"][:4],
        "inference": allocation["inference"],
        "detail": f'proposal source: {allocation["source"]}',
    }

    time.sleep(STEP_DELAY)

    tracker = credit_tracker.CreditTracker()
    status = tracker.status()
    yield {
        "step": 6, "name": "BUDGET", "status": "ok",
        "spent": status["spent_usd"], "budget": status["budget_usd"],
        "percent": status["percent_used"], "level": status["level"],
        "by_model": status["by_model"],
        "detail": f'${status["spent_usd"]:.4f} of ${status["budget_usd"]:.0f} ceiling',
    }

    time.sleep(STEP_DELAY)

    # step 7 - block until the human clicks, exactly like the CLI gate
    STATE["approval"] = None
    APPROVAL_EVENT.clear()
    yield {
        "step": 7, "name": "APPROVE", "status": "waiting",
        "allocation": allocation["allocation"],
        "detail": "nothing is dispatched until you approve",
    }
    APPROVAL_EVENT.wait(timeout=180)
    decision = STATE["approval"] or "timeout"

    if decision != "approve":
        yield {
            "step": 7, "name": "APPROVE", "status": "denied",
            "detail": f"decision: {decision} - nothing dispatched",
            "halted": True,
        }
        return

    yield {"step": 7, "name": "APPROVE", "status": "approved",
           "detail": "operator approved - dispatch released"}

    time.sleep(STEP_DELAY)

    scenario = STATE["scenario"]
    if scenario == "pump-critical":
        forced = {"hospital": 60, "water_pump": 40}
        rejected = allocator.validate_proposal(forced, town)
        yield {
            "step": 8, "name": "REPLAN", "status": "guardrail",
            "instruction": forced, "rejected": rejected,
            "applied": allocator.policy_solve(town),
            "detail": "human said pump 40 L - validator refused to starve the heart",
        }
    else:
        damaged = json.loads(json.dumps(town))
        damaged["reserve"]["total_litres"] = 80
        replanned = allocator.allocate(damaged, mode="policy")
        pump_lph = town["organs"]["water_pump"]["fuel_l_per_hour"]
        before = town["organs"]["water_pump"]["fuel_demand_litres"]
        after = replanned["allocation"].get("water_pump", 0)
        yield {
            "step": 8, "name": "REPLAN", "status": "replanned",
            "trigger": "depot damaged - 80 L usable instead of 100 L",
            "allocation": replanned["allocation"],
            "pump_before": round(before / pump_lph, 1),
            "pump_after": round(after / pump_lph, 1),
            "hospital_protected": replanned["allocation"].get("hospital") == 70,
            "detail": "same solver, new constraint, heart still protected",
        }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    fresh = False

    def log_message(self, *args):  # keep the console clean
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/events"):
            self.stream()
            return
        page = UI.read_bytes() if UI.exists() else b"<h1>live_ui.html missing</h1>"
        self._send(200, page, "text/html; charset=utf-8")

    def stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        run_id = uuid.uuid4().hex[:8]
        try:
            self.wfile.write(f"data: {json.dumps({'type': 'start', 'run': run_id})}\n\n".encode())
            self.wfile.flush()
            for step in pipeline(self.fresh):
                self.wfile.write(f"data: {json.dumps({'type': 'step', **step}, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
                if step.get("halted"):
                    break
                time.sleep(STEP_DELAY)
            self.wfile.write(f"data: {json.dumps({'type': 'done'})}\n\n".encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {}
        if self.path.startswith("/approve"):
            STATE["approval"] = payload.get("decision", "deny")
            APPROVAL_EVENT.set()
        elif self.path.startswith("/scenario"):
            STATE["scenario"] = payload.get("scenario", "reserve-loss")
        self._send(200, b'{"ok":true}', "application/json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LIFELINE AI live runner")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fresh", action="store_true", help="force a new Wonder call")
    args = parser.parse_args(argv)

    Handler.fresh = args.fresh
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"LIFELINE live  ->  http://127.0.0.1:{args.port}")
    print("  ctrl-c to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
