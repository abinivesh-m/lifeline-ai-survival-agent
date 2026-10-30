"""LIFELINE AI - the README is a test fixture.

    python -m pytest test_claims.py -q

Every number a judge can read - the test count, the dollars, the kilometres, the
litres - is quoted in prose somewhere: README, the page, a locale file. Prose
does not recompute itself. This file does: each claim is re-derived from the
artefact that produced it, so a stale sentence fails the build instead of
embarrassing the submission.

It also pins the retractions. A number that was removed because it could not be
sourced must not quietly come back, and the surfaces a judge reads are scanned
for it.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import a_star
import allocator
import field_reports

ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
TOWN = json.loads((ROOT / "town.json").read_text(encoding="utf-8"))


def _money(value: float, places: int) -> str:
    return f"{value:,.{places}f}"


def _collected_tests() -> int:
    """Ask pytest how many tests it collects, without running them."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    match = re.search(r"(\d+) tests? collected", out.stdout + out.stderr)
    assert match, f"could not read the collected count:\n{out.stdout}\n{out.stderr}"
    return int(match.group(1))


# --------------------------------------------------------------------------- #
# the claims
# --------------------------------------------------------------------------- #

def test_the_test_count_is_the_count_that_runs() -> None:
    count = _collected_tests()
    assert f"# {count} acceptance tests" in README, (
        f"README does not say '{count} acceptance tests' - run pytest, then update the prose"
    )
    assert f"8-step agent, {count} tests" in README
    page = (ROOT / "ui" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert f'"{count}/{count} pytest"' in page, "the badge on the page disagrees with pytest"


def test_the_ledger_total_matches_every_document_that_quotes_it() -> None:
    ledger = json.loads((ROOT / "credit_usage.json").read_text(encoding="utf-8"))
    entries = ledger["entries"]
    total = round(sum(float(e["cost_usd"]) for e in entries), 6)

    # the ledger's own totals, row by row
    assert round(sum(v["spent_usd"] for v in ledger["totals"].values()), 6) == total

    assert f"**${_money(total, 6)}**" in README, f"README does not quote ${_money(total, 6)}"
    assert f"${_money(total, 2)} of $150" in README
    # the verify() line a judge is told to reproduce, including the row count
    assert f"VERIFY OK - {len(entries)} entries, ${_money(total, 2)} spent" in README, (
        "the VERIFY line in the README is stale - run python credit_tracker.py verify"
    )

    # the page, and the committed snapshot the badge is reproducible from
    page = json.loads((ROOT / "ui" / "public" / "data" / "lifeline.json").read_text(encoding="utf-8"))
    assert round(page["credit"]["spent_usd"], 6) == total
    assert page["credit"]["ledger_rows"] == len(entries)

    proof = json.loads((ROOT / "artifacts" / "proof" / "credit_usage_live.json").read_text(encoding="utf-8"))
    assert round(sum(float(e["cost_usd"]) for e in proof["entries"]), 6) == total

    voice = ledger["totals"]["voice"]
    assert f"{voice['calls']} calls, ${_money(voice['spent_usd'], 6)}" in README, (
        "the Muse Voice Transcribe row in the README disagrees with the ledger"
    )


def test_the_route_and_the_allocation_are_recomputed_not_quoted() -> None:
    town = allocator.load_town()
    _, nodes, edges = a_star.load_network()
    route = a_star.plan_route(town, nodes, edges)
    allocation = allocator.policy_solve(town)

    assert route["distance_km"] == 7.8
    assert route["fuel_litres"] == 2.73
    assert route["saving"]["percent"] == 40.0
    assert allocation == {"hospital": 70, "water_pump": 30}

    # and the prose a judge reads is those numbers
    assert "| Route to hospital | 13.0 km bypass | **7.8 km** village road | **-5.2 km** |" in README
    assert "| Trip fuel | 4.55 L | 2.73 L | **-40%** |" in README
    assert "| Diesel reaching the town | split 50/50 | **70 / 30 exact** | no waste |" in README


def test_the_field_replan_artefact_is_what_the_solver_still_produces() -> None:
    committed = json.loads((ROOT / "artifacts" / "field_replan.json").read_text(encoding="utf-8"))
    reports = field_reports.from_artifact()
    assert len(committed["runs"]) == len(reports) > 0

    town = allocator.load_town()
    for stored, report in zip(committed["runs"], reports):
        fresh = field_reports.replan(town, field_reports.extract(report["transcript"], report["source"]))
        assert fresh["status"] == stored["status"], f"{report['source']}: status drifted"
        assert fresh["route_km_after"] == stored["route_km_after"]
        assert fresh["allocation_after"] == stored["allocation_after"]
        assert fresh["water_litres_lost"] == stored["water_litres_lost"]
        assert fresh["validator"] == stored["validator"]

    changed = next(r for r in committed["runs"] if r["status"] != "no_change")
    assert changed["route_km_before"] == 7.8 and changed["route_km_after"] == 13.0
    assert changed["route_fuel_after"] == 4.55
    assert changed["allocation_after"] == {"hospital": 70, "water_pump": 25}
    assert changed["pump_hours_after"] == 5.0
    assert changed["water_litres_lost"] == 4000

    # the page reads the artefact, so the panel and the README cannot disagree
    page = json.loads((ROOT / "ui" / "public" / "data" / "lifeline.json").read_text(encoding="utf-8"))
    panel = {run["source"]: run for run in page["field"]["runs"]}
    assert panel[changed["source"]]["allocation_after"] == changed["allocation_after"]
    assert panel[changed["source"]]["water_litres_lost"] == changed["water_litres_lost"]


def test_retracted_claims_do_not_come_back() -> None:
    """Numbers removed because they could not be sourced stay removed.

    DEMO_SCRIPT.md is exempt: a script that forbids a figure has to name it.
    Every surface a judge can read without the repo - the README, the page, the
    locale files, the town data - is scanned.
    """
    retired = [
        "3.5 billion",
        "3,5 milliards",
        "3,5 bilhões",
        "3.500 millones",
        "35 亿",
        "350 கோடி",
        "bilioni 3.5",
        "79/79",
        "79 tests",
        "79 acceptance tests",
    ]
    surfaces = [ROOT / "README.md", ROOT / "town.json", ROOT / "ui" / "app" / "page.tsx"]
    surfaces += sorted((ROOT / "locales").glob("*.json"))
    surfaces += sorted((ROOT / "ui" / "components").glob("*.tsx"))
    surfaces += sorted((ROOT / "ui" / "lib").glob("*.ts"))

    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for claim in retired:
            assert claim not in text, f"{path.relative_to(ROOT)} still carries the retired claim {claim!r}"


def test_every_artefact_the_readme_points_at_exists() -> None:
    """A README that cites a file must not cite a file that is not there.

    A row may say `capture needed` - that is the honest way to list a proof that
    has not been recorded yet, and it is the only exemption.
    """
    missing = []
    for line in README.splitlines():
        for path in re.findall(r"`(artifacts/[A-Za-z0-9_./-]+\.(?:json|txt|png|mp4|wav))`", line):
            if "capture needed" in line:
                continue
            if not (ROOT / path).exists():
                missing.append((path, line.strip()[:80]))
    assert not missing, f"README cites files that do not exist: {missing}"
