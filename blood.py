"""LIFELINE AI - blood intelligence: measure the diesel before you spend it.

Four deterministic calculations, all of them arithmetic over data this repo
already documents. None of them is a trained model, and every one of them says
so on screen.

  SWEAT     Diesel is bought by volume and burns by mass. At 42 C a litre is
            bigger than it is at 15 C, so 100 L bought hot carries less energy.
            The popular claim is "6 L lost". The physics says about 2.2 L.
            We publish the real number and the coefficient behind it.

  DNA       Every 10 L lot gets a birth certificate at the depot and a sha256
            hash chained to the lot before it. 100 L is ten lots: seven to the
            heart, three to the lungs. If 60 L arrives instead of 70 L, the
            missing lot is named, not estimated.

  CLOCK     Runtime is litres divided by burn rate. 70 L at 17.5 L/h is 4 h.
            Load changes the burn rate, so the clock moves. This is arithmetic,
            not a learned failure predictor - there is no failure-sound model
            here and we do not pretend there is.

  INVERSE   Allocate hours, not litres. "70 L" means nothing in a shelter at
            02:40; "four hours of heart" means everything.

What this module deliberately does NOT do: no blockchain, no token, no
consensus network (a hash chain is a hash chain), no audio-based failure
prediction, no handwriting OCR, no water-graph routing, no cattle-to-biogas
maths. Those need data this repo does not have, and inventing it is how a demo
dies under questioning.

Run:
    python blood.py --all
    python blood.py --sweat 42
    python blood.py --dna --shortfall 10
    python blood.py --clock 70 --load 1.2
    python blood.py --uptime
    python blood.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import allocator

ROOT = Path(__file__).parent

# --------------------------------------------------------------------------- #
# constants, with their provenance
# --------------------------------------------------------------------------- #

# Standard reference temperature for petroleum volume correction.
REFERENCE_C = 15.0

# Diesel density at 15 C. The 0.820-0.845 kg/L band is the usual range for
# automotive diesel; 0.835 is the midpoint and is used for every mass below.
DENSITY_KG_PER_L_15C = 0.835
DENSITY_BAND = (0.820, 0.845)

# Volumetric expansion coefficient for diesel, per degree C. Published values
# sit between 0.0008 and 0.00095. We use the low end, so the number we publish
# is the conservative one.
BETA_PER_C = 0.00084
BETA_BAND = (0.00080, 0.00095)

# The claim this replaces. Widely repeated, never sourced.
FOLKLORE_SWEAT_L = 6.0

GENESIS = "0" * 64


def _round(value: float, places: int = 4) -> float:
    return round(float(value), places)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# 1 - sweat
# --------------------------------------------------------------------------- #

def thermal(
    litres: float,
    temp_c: float = 42.0,
    beta: float = BETA_PER_C,
    reference_c: float = REFERENCE_C,
) -> dict[str, Any]:
    """Convert a volume measured hot to its 15 C equivalent.

    V15 = V_T / (1 + beta * (T - 15))

    Thermal expansion does not destroy diesel. It means a litre bought at 42 C
    contains less mass, and therefore less energy, than a litre bought at 15 C.
    That distinction is the whole point of showing this.
    """
    if litres < 0:
        raise ValueError("litres must be >= 0")
    if not BETA_BAND[0] <= beta <= BETA_BAND[1]:
        raise ValueError(f"beta outside the documented diesel band {BETA_BAND}")

    delta = temp_c - reference_c
    factor = 1.0 + beta * delta
    v15 = litres / factor
    deficit = litres - v15
    mass = v15 * DENSITY_KG_PER_L_15C

    # the honest range: same formula at both ends of the beta band
    low = litres / (1.0 + BETA_BAND[0] * delta)
    high = litres / (1.0 + BETA_BAND[1] * delta)

    return {
        "litres_measured": _round(litres, 2),
        "temp_c": _round(temp_c, 1),
        "reference_c": reference_c,
        "beta_per_c": beta,
        "litres_at_reference": _round(v15, 2),
        "deficit_litres": _round(deficit, 2),
        "deficit_percent": _round(deficit / litres * 100, 2) if litres else 0.0,
        "deficit_range_litres": (
            _round(min(litres - high, litres - low), 2),
            _round(max(litres - high, litres - low), 2),
        ),
        "mass_kg": _round(mass, 2),
        "density_kg_per_l": DENSITY_KG_PER_L_15C,
        "folklore_litres": FOLKLORE_SWEAT_L,
        "folklore_verdict": "not supported by the expansion coefficient",
        "note": (
            "Volume correction only. Expansion does not spill diesel; it means the "
            "tank holds less mass per litre when it is hot. Evaporation in a sealed "
            "tank is a separate, much smaller loss and is not claimed here."
        ),
    }


# --------------------------------------------------------------------------- #
# 2 - DNA
# --------------------------------------------------------------------------- #

def _lot_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_dna(
    town: dict,
    allocation: dict[str, int] | None = None,
    lot_litres: float = 10.0,
) -> dict[str, Any]:
    """Give every lot of diesel a hash-chained birth certificate.

    Lots are assigned in dispatch order: heart first, lungs second. That is the
    same order allocator.py enforces, so the ledger cannot contradict the plan.
    """
    reserve = float(town["reserve"]["total_litres"])
    if lot_litres <= 0:
        raise ValueError("lot_litres must be > 0")
    if reserve % lot_litres:
        raise ValueError("reserve must divide evenly into lots for a clean split")

    if allocation is None:
        allocation = allocator.allocate(town, mode="policy")["allocation"]

    # dispatch order, heart first
    order = ["hospital", "water_pump", "shelters"]
    remaining = {k: int(v) for k, v in allocation.items() if v}
    for key in list(remaining):
        if key not in order:
            raise ValueError(f"unknown organ in allocation: {key}")

    per_lot_mass = lot_litres * DENSITY_KG_PER_L_15C
    lots: list[dict[str, Any]] = []
    prev = GENESIS
    seq = 0

    for destination in order:
        litres = remaining.get(destination, 0)
        count = int(round(litres / lot_litres))
        if count * lot_litres != litres:
            raise ValueError(
                f"{destination} allocation {litres} L is not a whole number of "
                f"{lot_litres} L lots"
            )
        for _ in range(count):
            seq += 1
            payload = {
                "seq": seq,
                "litres": _round(lot_litres, 2),
                "mass_kg": _round(per_lot_mass, 3),
                "density_kg_per_l": DENSITY_KG_PER_L_15C,
                "reference_c": REFERENCE_C,
                "origin": "fuel_depot",
                "destination": destination,
                "prev": prev,
            }
            digest = _lot_hash(payload)
            lots.append({**payload, "hash": digest, "short": digest[:12]})
            prev = digest

    total = sum(lot["litres"] for lot in lots)
    return {
        "lot_litres": lot_litres,
        "lot_count": len(lots),
        "total_litres": _round(total, 2),
        "total_mass_kg": _round(sum(lot["mass_kg"] for lot in lots), 2),
        "split": {dest: sum(1 for l in lots if l["destination"] == dest) for dest in order},
        "lots": lots,
        "head": prev,
        "genesis": GENESIS,
        "algorithm": "sha256 over a canonical JSON payload, chained by prev",
        "note": (
            "A hash chain makes the record append-only: changing any past lot breaks "
            "every hash after it. It is not a blockchain and this repo does not claim "
            "one - there is no network, no token and no consensus."
        ),
    }


def verify_dna(ledger: dict[str, Any]) -> dict[str, Any]:
    """Recompute every hash. Returns the first point of tampering, if any."""
    prev = ledger.get("genesis", GENESIS)
    for index, lot in enumerate(ledger["lots"], start=1):
        payload = {k: v for k, v in lot.items() if k not in ("hash", "short")}
        if payload.get("prev") != prev:
            return {"ok": False, "at": index, "reason": "prev does not match the previous hash"}
        if _lot_hash(payload) != lot.get("hash"):
            return {"ok": False, "at": index, "reason": "hash does not match the payload"}
        prev = lot["hash"]
    if ledger.get("head") != prev:
        return {"ok": False, "at": len(ledger["lots"]), "reason": "head does not match the last hash"}
    return {"ok": True, "lots": len(ledger["lots"]), "head": prev}


def reconcile(
    ledger: dict[str, Any],
    received: dict[str, float] | None = None,
    shortfall_destination: str = "hospital",
    shortfall_litres: float = 0.0,
) -> dict[str, Any]:
    """Compare what left the depot with what was scanned in at each organ.

    A shortfall is expressed in missing lots, because that is what an operator
    can point at: "lot 7 never arrived", not "some diesel is missing".
    """
    if shortfall_litres:
        if shortfall_litres < 0:
            raise ValueError("shortfall_litres must be >= 0")
        # anything not named as short is assumed scanned in full, otherwise the
        # report would blame the pump for diesel nobody shorted
        full = {
            dest: sum(lot["litres"] for lot in ledger["lots"] if lot["destination"] == dest)
            for dest in {lot["destination"] for lot in ledger["lots"]}
        }
        full.update(received or {})
        full[shortfall_destination] = (
            full[shortfall_destination] - shortfall_litres
        )
        received = full

    if received is None:
        return {"status": "NO_SCAN", "note": "no delivery scan supplied"}

    lot_size = ledger["lot_litres"]
    report: dict[str, Any] = {"status": "RECONCILED", "organs": {}, "missing_lots": []}

    for destination in sorted({lot["destination"] for lot in ledger["lots"]}):
        dispatched = [lot for lot in ledger["lots"] if lot["destination"] == destination]
        expected = sum(lot["litres"] for lot in dispatched)
        got = float(received.get(destination, 0))
        missing = max(0.0, expected - got)
        missing_here = dispatched[len(dispatched) - int(round(missing / lot_size)):] if missing else []
        report["organs"][destination] = {
            "dispatched_litres": _round(expected, 2),
            "received_litres": _round(got, 2),
            "missing_litres": _round(missing, 2),
            "missing_lots": [lot["seq"] for lot in missing_here],
            "status": "SHORTFALL" if missing else "OK",
        }
        report["missing_lots"].extend(lot["seq"] for lot in missing_here)
        if missing:
            report["status"] = "SHORTFALL"

    chain = verify_dna(ledger)
    report["chain_ok"] = chain["ok"]
    report["note"] = (
        "Shortfall is a volume discrepancy at a scan point. It is evidence that a lot "
        "did not arrive, not evidence of who took it or why."
    )
    return report


# --------------------------------------------------------------------------- #
# 3 - clock
# --------------------------------------------------------------------------- #

def uptime(town: dict, organ: str, litres: float) -> dict[str, Any]:
    """Fuel-limited runtime for one organ, from its documented burn rate."""
    node = town["organs"][organ]
    if organ == "hospital":
        burn = float(node["generator_l_per_hour"])
        metric = "generator"
    elif organ == "water_pump":
        burn = float(node["fuel_l_per_hour"])
        metric = "pump"
    else:
        raise ValueError(f"{organ} has no fuel burn rate in town.json")

    if burn <= 0:
        raise ValueError("burn rate must be > 0")

    hours = litres / burn
    return {
        "organ": organ,
        "litres": _round(litres, 2),
        "burn_l_per_hour": burn,
        "hours": _round(hours, 2),
        "minutes": int(round(hours * 60)),
        "label": _label(hours),
        "metric": metric,
        "basis": f"town.json organs.{organ}.{'generator_l_per_hour' if organ == 'hospital' else 'fuel_l_per_hour'}",
    }


def death_clock(
    town: dict,
    litres: float,
    load: float = 1.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """When the heart stops, at a given electrical load.

    The nameplate burn is 17.5 L/h. Load is a multiplier on that burn, not a
    model of the generator's condition: a generator that is already failing can
    die before the fuel runs out, and this clock cannot see that.
    """
    if not 0.5 <= load <= 2.0:
        raise ValueError("load must be between 0.5 and 2.0")
    if litres < 0:
        raise ValueError("litres must be >= 0")

    base = float(town["organs"]["hospital"]["generator_l_per_hour"])
    burn = base * load
    hours = litres / burn if burn else 0.0
    start = now or _now()
    dies = start + timedelta(hours=hours)

    return {
        "litres": _round(litres, 2),
        "load_factor": _round(load, 2),
        "burn_l_per_hour": _round(burn, 2),
        "hours": _round(hours, 2),
        "minutes": int(round(hours * 60)),
        "dies_at": dies.isoformat(timespec="seconds"),
        "started_at": start.isoformat(timespec="seconds"),
        "label": _label(hours),
        "confidence": "arithmetic",
        "note": (
            "Fuel-limited runtime, not a failure prediction. Mechanical failure, "
            "fuel contamination and overload tripping all shorten this and are not "
            "modelled - because no failure-sound dataset exists in this repo."
        ),
    }


# --------------------------------------------------------------------------- #
# 4 - inverse
# --------------------------------------------------------------------------- #

def inverse(town: dict, allocation: dict[str, int] | None = None) -> dict[str, Any]:
    """The same plan, expressed in hours of life instead of litres."""
    if allocation is None:
        allocation = allocator.allocate(town, mode="policy")["allocation"]

    hospital_l = int(allocation.get("hospital", 0))
    pump_l = int(allocation.get("water_pump", 0))

    heart = uptime(town, "hospital", hospital_l)
    lungs = uptime(town, "water_pump", pump_l)

    pump_rate = float(town["organs"]["water_pump"]["delivers_litres_per_hour"])
    people = int(town["organs"]["shelters"]["people"])
    need_per_day = float(town["organs"]["shelters"]["water_litres_needed"])
    water_l = lungs["hours"] * pump_rate
    days = water_l / need_per_day if need_per_day else 0.0

    naive_heart = uptime(town, "hospital", 50)

    return {
        "heart": {
            "litres": heart["litres"],
            "label": heart["label"],
            "hours": heart["hours"],
        },
        "lungs": {
            "litres": lungs["litres"],
            "label": lungs["label"],
            "hours": lungs["hours"],
        },
        "water": {
            "litres_delivered": _round(water_l, 0),
            "people": people,
            "days_at_documented_demand": _round(days, 2),
            "demand_litres_per_day": need_per_day,
        },
        "naive_split": {
            "hospital_litres": 50,
            "heart_label": naive_heart["label"],
            "heart_hours": naive_heart["hours"],
        },
        "note": (
            "Runtime is fuel divided by the documented burn rate. The 90-minute "
            "figure in town.json baseline is measured pump uptime in the first four "
            "hours at duty cycle, which is a different metric and is not used here."
        ),
    }


def _label(hours: float) -> str:
    total = int(round(hours * 60))
    return f"{total // 60} h {total % 60:02d} m"


# --------------------------------------------------------------------------- #
# bundle + CLI
# --------------------------------------------------------------------------- #

def build(town: dict | None = None) -> dict[str, Any]:
    town = town or allocator.load_town()
    allocation = allocator.allocate(town, mode="policy")["allocation"]
    ledger = build_dna(town, allocation)

    return {
        "sweat": thermal(float(town["reserve"]["total_litres"]), 42.0),
        "dna": {k: v for k, v in ledger.items() if k != "lots"},
        "dna_lots": ledger["lots"][:10],
        "dna_verify": verify_dna(ledger),
        "clock": death_clock(town, float(allocation["hospital"]), 1.0),
        "clock_loaded": death_clock(town, float(allocation["hospital"]), 1.2),
        "inverse": inverse(town, allocation),
        "allocation": allocation,
        "honesty": [
            "sweat: volume correction with a published coefficient, not evaporation",
            "dna: sha256 hash chain over dispatch lots, not a blockchain",
            "clock: litres / burn rate, not a learned failure predictor",
            "inverse: the same numbers expressed in hours",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="blood intelligence over the diesel reserve")
    parser.add_argument("--sweat", nargs="?", const=42.0, type=float, metavar="TEMP_C")
    parser.add_argument("--dna", action="store_true")
    parser.add_argument("--shortfall", type=float, default=0.0)
    parser.add_argument("--clock", type=float, metavar="LITRES")
    parser.add_argument("--load", type=float, default=1.0)
    parser.add_argument("--uptime", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    town = allocator.load_town()

    if args.verify:
        ledger = build_dna(town)
        result = verify_dna(ledger)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1

    if args.all or not any([args.sweat is not None, args.dna, args.clock, args.uptime]):
        payload = build(town)
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        sweat = payload["sweat"]
        print("SWEAT")
        print(f'  {sweat["litres_measured"]:.0f} L at {sweat["temp_c"]:.0f} C  =  '
              f'{sweat["litres_at_reference"]:.2f} L at 15 C')
        print(f'  deficit {sweat["deficit_litres"]:.2f} L ({sweat["deficit_percent"]:.2f}%), '
              f'range {sweat["deficit_range_litres"]}, folk claim {sweat["folklore_litres"]:.0f} L')
        print("\nDNA")
        print(f'  {payload["dna"]["lot_count"]} lots of {payload["dna"]["lot_litres"]:.0f} L, '
              f'split {payload["dna"]["split"]}')
        print(f'  head {payload["dna"]["head"][:32]}...  verify {payload["dna_verify"]["ok"]}')
        print("\nCLOCK")
        for key in ("clock", "clock_loaded"):
            clock = payload[key]
            print(f'  {clock["litres"]:.0f} L at load {clock["load_factor"]:.1f}  ->  '
                  f'{clock["label"]}  (burn {clock["burn_l_per_hour"]} L/h)')
        print("\nINVERSE")
        inv = payload["inverse"]
        print(f'  heart {inv["heart"]["litres"]} L = {inv["heart"]["label"]}, '
              f'lungs {inv["lungs"]["litres"]} L = {inv["lungs"]["label"]}')
        print(f'  water {inv["water"]["litres_delivered"]:.0f} L = '
              f'{inv["water"]["days_at_documented_demand"]} days for {inv["water"]["people"]} people')
        print(f'  naive 50 L split = {inv["naive_split"]["heart_label"]} of heart')
        return 0

    if args.sweat is not None:
        print(json.dumps(thermal(100.0, args.sweat), indent=2))
        return 0

    if args.dna:
        ledger = build_dna(town)
        if args.shortfall:
            report = reconcile(ledger, shortfall_litres=args.shortfall)
        else:
            report = reconcile(ledger, received={
                "hospital": sum(l["litres"] for l in ledger["lots"] if l["destination"] == "hospital"),
                "water_pump": sum(l["litres"] for l in ledger["lots"] if l["destination"] == "water_pump"),
            })
        if args.json:
            print(json.dumps({"ledger": {k: v for k, v in ledger.items() if k != "lots"},
                              "lots": ledger["lots"], "reconcile": report}, indent=2))
            return 0
        for lot in ledger["lots"]:
            print(f'  lot {lot["seq"]:02d}  {lot["litres"]:5.1f} L  {lot["mass_kg"]:6.3f} kg  '
                  f'{lot["destination"]:11s} {lot["short"]}')
        print(f'  head {ledger["head"]}')
        print(f'  verify {verify_dna(ledger)}')
        print(f'  reconcile {report["status"]} missing_lots={report["missing_lots"]}')
        return 0

    if args.clock is not None:
        print(json.dumps(death_clock(town, args.clock, args.load), indent=2))
        return 0

    if args.uptime:
        print(json.dumps(inverse(town), indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

