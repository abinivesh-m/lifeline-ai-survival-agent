"""LIFELINE AI - the field-report -> constraint -> replan loop.

    python -m pytest test_field_reports.py -q

Every test here corresponds to a claim the README and the demo make about the
loop. The point of the module is that a transcript cannot invent a number, so
most of these tests are about what it refuses to do.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import a_star
import allocator
import field_reports

ROOT = Path(__file__).parent
TOWN = json.loads((ROOT / "town.json").read_text(encoding="utf-8"))


def _kinds(constraints: list[dict]) -> list[str]:
    return [c["kind"] for c in constraints]


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #

def test_extracts_blocked_village_road() -> None:
    found = field_reports.extract("The village road is washed out near the junction.")
    assert _kinds(found) == ["road_blocked"]
    assert found[0]["value"] == "Kottur village road"


def test_extracts_from_the_real_tamil_transcript() -> None:
    data = json.loads((ROOT / "artifacts" / "voice_reports.json").read_text(encoding="utf-8"))
    transcript = data["reports"][0]["transcript"]
    found = field_reports.extract(transcript)
    assert "road_blocked" in _kinds(found)
    assert "closure_hours" in _kinds(found)
    hours = next(c for c in found if c["kind"] == "closure_hours")
    assert hours["value"] == 6


def test_every_constraint_quotes_the_words_that_produced_it() -> None:
    transcript = "The depot tank is cracked. Only 80 litres survive."
    for c in field_reports.extract(transcript):
        assert c["span"], "a constraint with no span cannot be audited"
        assert c["span"] in transcript or c["span"].strip() in transcript


def test_unrelated_speech_yields_nothing() -> None:
    assert field_reports.extract("The baby is fine and the rain has stopped.") == []


def test_unnamed_road_is_not_actionable() -> None:
    """"The road is closed" names no road, so it must not block one."""
    found = field_reports.extract("The road is closed somewhere.")
    assert "road_blocked" not in _kinds(found)


def test_empty_transcript_yields_nothing() -> None:
    assert field_reports.extract("") == []


# --------------------------------------------------------------------------- #
# the replan
# --------------------------------------------------------------------------- #

def test_village_road_block_moves_the_plan() -> None:
    found = field_reports.extract("The village road is washed out near the junction.")
    result = field_reports.replan(TOWN, found)

    assert result["status"] == "replanned"
    # the detour is the 13.0 km bypass, so the 40% saving the agent found is gone
    assert result["route_km_before"] == 7.8
    assert result["route_km_after"] == 13.0
    assert result["route_fuel_before"] == 2.73
    assert result["route_fuel_after"] == 4.55
    # 1.82 L more, floored to the 5 L unit -> 95 L usable
    assert result["reserve_after"] == 95
    assert result["allocation_after"] == {"hospital": 70, "water_pump": 25}
    assert result["pump_hours_before"] == 6.0
    assert result["pump_hours_after"] == 5.0
    assert result["water_litres_lost"] == 4000
    assert result["validator"] == []


def test_depot_loss_reaches_the_same_answer_as_the_cli_scenario() -> None:
    found = field_reports.extract("The depot tank is cracked. Only 80 litres survive.")
    result = field_reports.replan(TOWN, found)
    assert result["reserve_after"] == 80
    assert result["allocation_after"] == {"hospital": 70, "water_pump": 10}
    assert result["pump_hours_after"] == 2.0
    assert result["water_litres_lost"] == 16000
    assert result["validator"] == []


def test_a_longer_closure_is_reported_as_a_shortfall_not_rescaled() -> None:
    found = field_reports.extract("The road at km 42 is closed. It will stay closed for nine hours.")
    result = field_reports.replan(TOWN, found)
    assert result["status"] == "shortfall"
    assert result["shortfall_litres"] == 52.5  # 3 extra hours x 17.5 L/h
    # the hospital's stated demand is not quietly shrunk to make the sum fit
    assert result["allocation_after"] == {"hospital": 70, "water_pump": 30}


def test_the_real_report_changes_nothing_and_says_so() -> None:
    data = json.loads((ROOT / "artifacts" / "voice_reports.json").read_text(encoding="utf-8"))
    found = field_reports.extract(data["reports"][0]["transcript"])
    result = field_reports.replan(TOWN, found)
    assert result["status"] == "no_change"
    assert result["changes"] == []
    assert result["allocation_after"] == result["allocation_before"]


def test_replan_never_mutates_the_town_it_was_given() -> None:
    before = copy.deepcopy(TOWN)
    found = field_reports.extract("The village road is washed out.")
    field_reports.replan(TOWN, found)
    assert TOWN == before, "the caller's town must survive a replan unchanged"


def test_replan_without_constraints_is_a_no_op() -> None:
    result = field_reports.replan(TOWN, [])
    assert result["status"] == "no_change"
    assert result["allocation_before"] == {"hospital": 70, "water_pump": 30}


def test_unroutable_network_is_reported_not_crashed() -> None:
    blocked = [{"kind": "road_blocked", "value": road, "unit": None, "span": "test", "source": "t", "confidence": 1.0}
               for road in ("Kottur village road", "Kottur bypass", "Kottur south link", "NH-544", "pump feeder road")]
    result = field_reports.replan(TOWN, blocked)
    assert result["status"] == "unroutable"
    assert result["allocation_after"] is None
    assert "RoutingError" in result["evidence"] or "no open road" in result["detail"]


def test_agent_step_8_consumes_step_2() -> None:
    """The loop is wired: LISTEN's constraints are what REPLAN acts on."""
    import agent

    listen = agent.step_listen(TOWN)
    assert listen["constraints"], "step 2 produced no constraints from the stored reports"
    replan = agent.step_replan(TOWN, "field-report", listen=listen)
    assert replan["step"] == 8
    assert replan["constraints"] == listen["constraints"]
    # report_01 confirms the closure; report_02 blocks the village road and moves the plan
    assert replan["status"] == "replanned"
    assert replan["allocation_after"] == {"hospital": 70, "water_pump": 25}


def test_the_second_report_is_labelled_synthetic() -> None:
    """Nothing may claim a synthesised clip is a field recording."""
    data = json.loads((ROOT / "artifacts" / "voice_reports.json").read_text(encoding="utf-8"))
    files = {r["file"]: r for r in data["reports"]}
    assert "report_02.wav" in files
    assert files["report_02.wav"]["synthetic"] is True
