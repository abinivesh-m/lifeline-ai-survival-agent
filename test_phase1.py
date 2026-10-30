"""LIFELINE AI - Phase 1 acceptance tests. Standard library only.

    python test_phase1.py

Every assertion here corresponds to a claim made in the README or the demo
video. If a number changes, this file fails before a judge finds it.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import agent
import a_star
import allocator
import credit_tracker
import dependency_graph
import escalation
import export_ui_data
import multilingual
import seri_gate

ROOT = Path(__file__).parent
TOWN = json.loads((ROOT / "town.json").read_text(encoding="utf-8"))

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - a test runner reports everything
        FAILED.append((name, f"{type(exc).__name__}: {exc}"))
    else:
        PASSED.append(name)


def eq(actual, expected, label: str = "") -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def approx(actual: float, expected: float, tol: float, label: str = "") -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"{label}: expected {expected} +/- {tol}, got {actual}")


# --------------------------------------------------------------------------- #
# town.json
# --------------------------------------------------------------------------- #

def test_town_identity() -> None:
    town = TOWN["town"]
    eq(town["name"], "Kottur")
    approx(town["lat"], 11.0168, 1e-6, "lat")
    approx(town["lon"], 76.9558, 1e-6, "lon")
    eq(town["taluk"], "Pollachi")
    eq(town["people_at_risk"], 200)


def test_reserve_math() -> None:
    organs = TOWN["organs"]
    total = TOWN["reserve"]["total_litres"]
    demand = sum(n.get("fuel_demand_litres", 0) for n in organs.values())
    eq(total, 100, "reserve")
    eq(demand, 100, "sum of demands")
    eq(organs["hospital"]["fuel_demand_litres"], 70)
    eq(organs["water_pump"]["fuel_demand_litres"], 30)


def test_dependency_edges() -> None:
    organs = TOWN["organs"]
    eq(organs["hospital"]["depends_on"], ["fuel_depot"])
    eq(organs["water_pump"]["depends_on"], ["hospital"])
    eq(organs["shelters"]["depends_on"], ["water_pump"])
    eq(organs["hospital"]["priority"], 1, "hospital is priority 1")


def test_crisis_numbers() -> None:
    crisis = TOWN["crisis"]
    eq(crisis["blocked_corridor_km"], 4.2)
    eq(crisis["expected_clear_hours"], 6)
    eq(TOWN["organs"]["hospital"]["runtime_hours_left"], 4.0)


# --------------------------------------------------------------------------- #
# dependency_graph.py
# --------------------------------------------------------------------------- #

def test_topological_order() -> None:
    eq(
        dependency_graph.kahn_order(TOWN),
        ["fuel_depot", "hospital", "water_pump", "shelters"],
    )


def test_cycle_is_rejected() -> None:
    broken = json.loads(json.dumps(TOWN))
    broken["organs"]["fuel_depot"]["depends_on"] = ["shelters"]
    try:
        dependency_graph.kahn_order(broken)
    except dependency_graph.CycleError:
        return
    raise AssertionError("cycle was not detected")


def test_unknown_dependency_is_rejected() -> None:
    broken = json.loads(json.dumps(TOWN))
    broken["organs"]["hospital"]["depends_on"] = ["ghost"]
    try:
        dependency_graph.prerequisites(broken)
    except dependency_graph.DependencyError:
        return
    raise AssertionError("dangling dependency was not detected")


def test_cascade_from_hospital() -> None:
    blast = dependency_graph.cascade(TOWN, ["hospital"])
    eq(blast["downstream_failed"], ["water_pump", "shelters"])
    eq(blast["people_affected"], 200)


def test_cascade_from_depot() -> None:
    blast = dependency_graph.cascade(TOWN, ["fuel_depot"])
    eq(blast["total_down"], ["fuel_depot", "hospital", "water_pump", "shelters"])


def test_funding_order_hospital_first() -> None:
    plan = dependency_graph.funding_order(TOWN)
    eq([p["organ"] for p in plan][:3], ["fuel_depot", "hospital", "water_pump"])
    eq(plan[1]["demand_litres"], 70)
    eq(plan[2]["demand_litres"], 30)


def test_validate_clean_town() -> None:
    eq(dependency_graph.validate(TOWN), [])


def test_critical_path() -> None:
    cp = dependency_graph.critical_path(TOWN)
    eq(cp["path"], ["fuel_depot", "hospital", "water_pump", "shelters"])
    eq(cp["depth"], 3)


# --------------------------------------------------------------------------- #
# a_star.py
# --------------------------------------------------------------------------- #

def _brute_force_shortest(nodes, edges, start, goal) -> float:
    """Independent oracle: enumerate every simple path."""
    graph = a_star.build_adjacency(edges)
    best = float("inf")

    def walk(node, visited, cost):
        nonlocal best
        if node == goal:
            best = min(best, cost)
            return
        for neighbour, weight, _ in graph.get(node, []):
            if neighbour not in visited and cost + weight < best:
                walk(neighbour, visited | {neighbour}, cost + weight)

    walk(start, {start}, 0.0)
    return best


def test_heuristic_admissible() -> None:
    _, nodes, edges = a_star.load_network()
    eq(a_star.audit(nodes, edges), [])


def test_route_is_the_7_8_km_village_road() -> None:
    town, nodes, edges = a_star.load_network()
    report = a_star.plan_route(town, nodes, edges)
    eq(report["path"], ["fuel_depot", "village_jn", "water_pump", "hospital"])
    approx(report["distance_km"], 7.8, 1e-6, "distance")


def test_route_avoided_the_landslide() -> None:
    town, nodes, edges = a_star.load_network()
    report = a_star.plan_route(town, nodes, edges)
    pairs = set(zip(report["path"], report["path"][1:]))
    if ("slide_gate", "hospital") in pairs or ("hospital", "slide_gate") in pairs:
        raise AssertionError("route drove through the blocked corridor")
    eq(len(report["blocked_corridors"]), 1)


def test_astar_is_optimal() -> None:
    town, nodes, edges = a_star.load_network()
    graph = a_star.build_adjacency(edges)
    route = a_star.a_star(nodes, graph, "fuel_depot", "hospital")
    oracle = _brute_force_shortest(nodes, edges, "fuel_depot", "hospital")
    approx(route.km, oracle, 1e-9, "A* vs brute force")


def test_blocking_changes_the_answer() -> None:
    town, nodes, edges = a_star.load_network()
    graph_open = a_star.build_adjacency(edges, include_blocked=True)
    direct = a_star.a_star(nodes, graph_open, "fuel_depot", "hospital")
    approx(direct.km, 4.2, 1e-6, "direct corridor")
    eq(direct.path, ["fuel_depot", "slide_gate", "hospital"])


def test_savings_are_40_percent() -> None:
    town, nodes, edges = a_star.load_network()
    report = a_star.plan_route(town, nodes, edges)
    approx(report["saving"]["percent"], 40.0, 1e-6, "percent saved")
    approx(report["saving"]["km"], 5.2, 1e-6, "km saved")
    approx(report["saving"]["fuel_litres"], 1.82, 1e-6, "fuel saved")
    approx(report["saving"]["generator_minutes_bought"], 6.2, 0.05, "generator minutes")


def test_unreachable_goal_raises() -> None:
    _, nodes, _ = a_star.load_network()
    try:
        a_star.a_star(nodes, {}, "fuel_depot", "hospital")
    except a_star.RoutingError:
        pass
    else:
        raise AssertionError("expected RoutingError on an empty road network")
    try:
        a_star.a_star(nodes, {}, "fuel_depot", "atlantis")
    except a_star.RoutingError:
        return
    raise AssertionError("expected RoutingError for an unknown goal")


# --------------------------------------------------------------------------- #
# allocator.py
# --------------------------------------------------------------------------- #

def test_allocation_is_exact_100() -> None:
    result = allocator.allocate(TOWN, mode="policy")
    eq(result["allocation"], {"hospital": 70, "water_pump": 30})
    eq(result["total"], 100)


def test_allocation_matches_town_demands() -> None:
    result = allocator.allocate(TOWN, mode="policy")
    for organ, litres in result["allocation"].items():
        eq(litres, TOWN["organs"][organ]["fuel_demand_litres"], organ)


def test_evidence_sources_resolve() -> None:
    result = allocator.allocate(TOWN, mode="policy")
    for item in result["evidence"]:
        _, _, path = item["source"].partition("#")
        node = TOWN
        for part in path.split("."):
            node = node[part]
        eq(item["value"], node, item["source"])


def test_inference_references_real_evidence() -> None:
    result = allocator.allocate(TOWN, mode="policy")
    ids = {item["id"] for item in result["evidence"]}
    for item in result["inference"]:
        missing = set(item["because"]) - ids
        eq(missing, set(), f"inference cites missing evidence {missing}")


def test_over_allocation_is_rejected() -> None:
    problems = allocator.validate_proposal({"hospital": 90, "water_pump": 10}, TOWN)
    if not any("exceeds stated demand" in p for p in problems):
        raise AssertionError(f"over-allocation not rejected: {problems}")


def test_wrong_total_is_rejected() -> None:
    problems = allocator.validate_proposal({"hospital": 70, "water_pump": 20}, TOWN)
    if not any("does not match reserve" in p for p in problems):
        raise AssertionError(f"short total not rejected: {problems}")


def test_priority_starvation_is_rejected() -> None:
    problems = allocator.validate_proposal({"hospital": 60, "water_pump": 40}, TOWN)
    if not any("under-funded" in p for p in problems):
        raise AssertionError(f"starving the hospital not rejected: {problems}")


def test_unknown_organ_is_rejected() -> None:
    problems = allocator.validate_proposal({"hospital": 70, "shelters": 30}, TOWN)
    if not any("not a diesel-consuming organ" in p for p in problems):
        raise AssertionError(f"unknown organ not rejected: {problems}")


def test_human_gate_is_closed() -> None:
    result = allocator.allocate(TOWN, mode="policy")
    eq(result["human_approval_required"], True)
    eq(result["executed"], False)
    if "medical" not in result["safety"]:
        raise AssertionError("medical-advice guardrail missing")


def test_offline_mode_makes_no_call() -> None:
    os.environ["LIFELINE_OFFLINE"] = "1"
    try:
        result = allocator.allocate(TOWN, mode="auto")
        eq(result["source"], "policy")
        eq(result["trace"]["wonder"]["status"], "unconfigured")
    finally:
        os.environ.pop("LIFELINE_OFFLINE", None)


def test_allocator_and_graph_agree() -> None:
    """The fuel order must obey the dependency order, not just priority."""
    result = allocator.allocate(TOWN, mode="policy")
    order = [o for o in dependency_graph.kahn_order(TOWN) if o in result["allocation"]]
    eq(order, ["hospital", "water_pump"])


# --------------------------------------------------------------------------- #
# credit_tracker.py
# --------------------------------------------------------------------------- #

def _tracker() -> credit_tracker.CreditTracker:
    directory = tempfile.mkdtemp()
    return credit_tracker.CreditTracker(ledger_path=Path(directory) / "credit_usage.json")


def test_plan_totals_150() -> None:
    eq(round(credit_tracker.PLANNED_TOTAL, 2), 150.0)


def test_warn_threshold_at_120() -> None:
    t = _tracker()
    t.log("sam", calls=20)  # 30
    t.log("voice", calls=50)  # 60 -> 90
    t.log("spark", calls=40)  # 80 -> 110
    eq(t.level(), "ok")
    t.log("wonder", calls=100)  # ~41.2 -> ~121.2, past the 80% alert
    eq(t.level(), "warn")
    if not any("WARN" in a for a in t.alerts()):
        raise AssertionError(t.alerts())


def test_critical_threshold_at_142_5() -> None:
    t = _tracker()
    t.log("wonder", calls=170)  # 70
    t.log("sam", calls=20)  # 100
    t.log("voice", calls=50)  # 130
    t.log("spark", calls=25)  # 142.5
    approx(t.spend(), 142.5, 1e-9, "spend at threshold")
    eq(t.level(), "critical")


def test_bucket_overflow_is_refused() -> None:
    t = _tracker()
    t.log("sam", calls=20)
    try:
        t.log("sam", calls=1)
    except credit_tracker.BudgetError:
        return
    raise AssertionError("bucket overflow was allowed")


def test_overspend_is_refused() -> None:
    t = _tracker()
    try:
        t.log("wonder", calls=171)
    except credit_tracker.BudgetError:
        return
    raise AssertionError("over-budget call was allowed")


def test_full_plan_verifies_and_persists() -> None:
    t = _tracker()
    for model, calls in [("wonder", 170), ("sam", 20), ("voice", 50), ("spark", 40)]:
        t.log(model, calls=calls, note="test")
    eq(t.verify(), [])
    approx(t.spend(), 150.0, 1e-9, "total spend")

    reloaded = credit_tracker.CreditTracker(ledger_path=t.path)
    eq(len(reloaded.entries), 4)
    approx(reloaded.spend(), 150.0, 1e-9, "reloaded spend")
    Path(t.path).unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# end-to-end
# --------------------------------------------------------------------------- #

def test_end_to_end_story() -> None:
    """The demo's numbers, computed together, never hardcoded."""
    town, nodes, edges = a_star.load_network()
    route = a_star.plan_route(town, nodes, edges)
    allocation = allocator.allocate(town, mode="policy")
    order = dependency_graph.kahn_order(town)

    eq(route["distance_km"], 7.8)
    eq(route["saving"]["percent"], 40.0)
    eq(allocation["allocation"], {"hospital": 70, "water_pump": 30})
    eq(allocation["total"], 100)
    eq(order, ["fuel_depot", "hospital", "water_pump", "shelters"])

    # Step 7 must arm the ladder for every locale and claim nothing was sent.
    approval = agent.step_approve(allocation, town, auto=True)
    ladder = approval["escalation"]
    eq(ladder["tier"], 1)
    eq(len(ladder["languages"]), 8)
    eq(ladder["payloads_per_language"], 9)
    eq(ladder["payloads_total"], 72)
    eq(sorted(ladder["channels"]), ["sms", "voice_call", "whatsapp"])
    eq(ladder["status"], "PENDING_CREDENTIALS")

    # The tier-2 payload comes from the model-drafted artefact when one is on
    # file. A spoken payload may only point at a clip that exists on disk.
    payloads = escalation.notifications(2, town, "ta")
    eq(len(payloads), 9)
    eq({payload["channel"] for payload in payloads}, {"sms", "voice_call", "whatsapp"})
    eq({payload["status"] for payload in payloads}, {"PENDING_CREDENTIALS"})
    eq(len({payload["body"] for payload in payloads}), 1)
    for payload in payloads:
        if payload["audio"]:
            eq((ROOT / payload["audio"]).exists(), True)
            eq(payload["channel"], "voice_call")
    drafted = escalation.drafted_for("ta")
    if drafted and drafted["sms"]["valid"]:
        eq(payloads[0]["body"], drafted["sms"]["body"])
        eq(payloads[0]["source"], "model-drafted")

    # The validator is the last word on numbers, not the reviewer model.
    bad = multilingual.validate_body("Send 999 L, give 2 mg insulin at once", "ta")
    eq(bad["ok"], False)
    if multilingual.ARTIFACT.exists():
        eq(multilingual.verify(), [])

    # The Seri Gate: the word, the model and the code must agree. Denial wins,
    # Tamil negation is a suffix (so "சரியில்லை" is one token, not a prefix),
    # and an ASR echo ("சரிசரி") can only collapse when it is an exact double.
    eq(seri_gate.token_intent("சரி"), "APPROVE")
    eq(seri_gate.token_intent("sariசரி அனுமதிக்கிறேன்."), "APPROVE")
    eq(seri_gate.token_intent("சரிசரி"), "APPROVE")
    eq(seri_gate.token_intent("சரியில்லை"), "DENY")
    eq(seri_gate.token_intent("not ok"), "DENY")
    eq(seri_gate.token_intent("Ansari,"), "UNCLEAR")
    eq(seri_gate.token_intent("maybe"), "UNCLEAR")
    eq(seri_gate.token_intent("Yes, I approve.", "en"), "APPROVE")
    eq(seri_gate.token_intent("Sí, apruebo.", "es"), "APPROVE")
    eq(seri_gate.token_intent("Oui, j'approuve.", "fr"), "APPROVE")
    eq(seri_gate.token_intent("نعم، أوافق.", "ar"), "APPROVE")
    eq(seri_gate.token_intent("Sim, aprovo.", "pt"), "APPROVE")
    eq(seri_gate.token_intent("Ndiyo, nakubali.", "sw"), "APPROVE")
    # The real ASR spellings, not the textbook ones: native-name bias made the
    # transcriber return these shortened/alternate forms, and the gate must
    # recognise the word that was actually heard.
    eq(seri_gate.token_intent("Ndio na kubali.", "sw"), "APPROVE")
    eq(seri_gate.token_intent("أوفقوا", "ar"), "APPROVE")
    eq(seri_gate.token_intent("Sim", "pt"), "APPROVE")
    eq(seri_gate.token_intent("Sí", "es"), "APPROVE")
    eq(seri_gate.token_intent("No, nunca.", "es"), "DENY")
    eq(seri_gate.token_intent("Non, jamais.", "fr"), "DENY")
    eq(seri_gate.token_intent("Hapana.", "sw"), "DENY")
    heard = {"status": "answered", "intent": "APPROVE", "confidence": 0.99}
    eq(seri_gate.decide("சரி", heard)["approved"], True)
    eq(seri_gate.decide("Sí, apruebo.", heard, "es")["approved"], True)
    eq(seri_gate.decide("சரி", {**heard, "confidence": 0.5})["approved"], False)
    eq(seri_gate.decide("சரியில்லை", heard)["approved"], False)
    eq(seri_gate.decide("maybe", heard)["approved"], False)
    if seri_gate.ARTIFACT.exists():
        artifact = json.loads(seri_gate.ARTIFACT.read_text(encoding="utf-8"))
        locales = artifact.get("locales", [])
        if locales:
            eq(artifact["summary"]["languages"], len(locales))
            eq(
                artifact["summary"]["approved"],
                sum(1 for entry in locales if entry["gate"]["approved"]),
            )
            for entry in locales:
                if not entry["gate"]["approved"]:
                    continue
                eq(bool(entry["ledger"]), True)
                eq(entry["ledger"]["detail"]["audio_sha256"], entry["audio"]["sha256"])
                eq(entry["ledger"]["detail"]["locale"], entry["locale"])
            eq(escalation.HashLedger().verify(), [])

    # Trap 2: an offline run must not erase the open-weight evidence. When the
    # latest run is policy-only, the exporter falls back to the newest valid
    # proof, labelled STORED RUN - never LIVE CALL.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "runs").mkdir()
        (root / "artifacts").mkdir()
        (root / "runs" / "latest.json").write_text(json.dumps({
            "generated_utc": "2026-10-27T00:00:00+00:00",
            "steps": [{
                "name": "ALLOCATE",
                "source": "policy",
                "allocation": {"hospital": 70, "water_pump": 30},
                "trace": {},
            }],
        }), encoding="utf-8")
        (root / "artifacts" / "openweight_proof.json").write_text(json.dumps({
            "provider": "Baseten",
            "model": "meta-models/muse-spark-open-1026",
            "runs": [{
                "valid": True,
                "latency_s": 4.44,
                "at": "2026-10-27T00:00:00+00:00",
                "allocation": {"hospital": 70, "water_pump": 30},
                "justification": "stored run",
                "confidence": 0.99,
                "model": "meta-models/muse-spark-open-1026",
                "provider": "Baseten",
            }],
        }), encoding="utf-8")
        original_root = export_ui_data.ROOT
        export_ui_data.ROOT = root
        try:
            brain = export_ui_data._latest_run_brain()
        finally:
            export_ui_data.ROOT = original_root
        eq(brain["source"], "openweight-stored")
        eq(brain["status"], "stored")
        eq(brain["valid"], True)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tests = [(name, obj) for name, obj in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        check(name, fn)

    for name in PASSED:
        print(f"  PASS  {name}")
    for name, error in FAILED:
        print(f"  FAIL  {name}\n        {error}")

    total = len(PASSED) + len(FAILED)
    print(f"\n{len(PASSED)}/{total} passed")
    if FAILED:
        print("PHASE 1 NOT READY")
        return 1
    print("PHASE 1 READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
