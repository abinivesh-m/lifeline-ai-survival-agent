"""Tests for the two survivor protocols.

The relay tests use an explicitly synthetic water edge and say so in the
edge label. Nothing here claims Kottur has a surveyed canal.
"""

from __future__ import annotations

from dataclasses import replace

import protocols
from a_star import Edge


def network():
    return protocols.a_star.load_network()[1:]


def closed(edges):
    return [replace(edge, status="blocked", reason="test closure") for edge in edges]


def test_relay_uses_road_when_the_road_is_open():
    nodes, edges = network()
    report = protocols.snake_boat_relay(nodes, edges)
    assert report["mode"] == "road"
    assert report["switched"] is False
    assert report["water_edges"] == 0
    assert report["km"] == 7.8
    assert report["path"] == ["fuel_depot", "village_jn", "water_pump", "hospital"]


def test_relay_refuses_rather_than_inventing_a_river():
    nodes, edges = network()
    report = protocols.snake_boat_relay(nodes, closed(edges))
    assert report["mode"] == "none"
    assert report["switched"] is False
    assert report["armed"] is True
    assert report["km"] is None
    assert report["path"] == []
    assert "0 surveyed water" in report["note"]
    assert "no open route" in (report.get("error") or "")


def test_relay_switches_to_a_surveyed_water_edge():
    nodes, edges = network()
    canal = Edge(
        src="fuel_depot",
        dst="hospital",
        km=9.9,
        road="SYNTHETIC test canal (not a Kottur survey)",
        status="open",
    )
    report = protocols.snake_boat_relay(nodes, closed(edges), water_edges=[canal])
    assert report["mode"] == "water"
    assert report["switched"] is True
    assert report["water_edges"] == 1
    assert report["km"] == 9.9
    assert report["path"] == ["fuel_depot", "hospital"]


def test_ant_pheromone_finds_the_bypass():
    nodes, edges = network()
    report = protocols.ant_pheromone(nodes, edges)
    assert report["best_km"] == 7.8
    assert report["best_path"] == ["fuel_depot", "village_jn", "water_pump", "hospital"]
    assert report["best_path"][1] != "slide_gate", "the blocked corridor must never be on the path"


def test_ant_pheromone_learns_the_block():
    nodes, edges = network()
    report = protocols.ant_pheromone(nodes, edges)
    assert report["learned_after"] is not None
    assert report["learned_after"] < report["iterations"] + 1
    assert report["blocked_share_final"] < 0.01
    assert report["blocked_share_final"] < report["history"][0]["blocked_share"]


def test_ant_pheromone_is_reproducible():
    nodes, edges = network()
    first = protocols.ant_pheromone(nodes, edges)
    second = protocols.ant_pheromone(nodes, edges)
    assert first == second


def test_build_reports_both_protocols():
    report = protocols.build()
    assert report["snake_boat_relay"]["mode"] == "road"
    assert report["ant_pheromone"]["best_km"] == 7.8
    assert report["ant_pheromone"]["runs"] == 144
