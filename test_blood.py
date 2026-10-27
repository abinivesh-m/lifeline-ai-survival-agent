"""Tests for blood.py - the four deterministic calculations.

    python -m pytest test_blood.py -q
    python test_blood.py

Every assertion is against a number derived from town.json, so a change to the
scenario that silently changes an on-screen figure fails here first.
"""

from __future__ import annotations

import unittest

import allocator
import blood


class TestSweat(unittest.TestCase):
    def setUp(self) -> None:
        self.town = allocator.load_town()
        self.reserve = float(self.town["reserve"]["total_litres"])

    def test_reference_conversion(self) -> None:
        result = blood.thermal(100.0, 42.0)
        self.assertAlmostEqual(result["litres_at_reference"], 97.78, places=2)
        self.assertAlmostEqual(result["deficit_litres"], 2.22, places=2)

    def test_mass_uses_documented_density(self) -> None:
        result = blood.thermal(100.0, 42.0)
        self.assertAlmostEqual(result["mass_kg"], 97.78 * 0.835, places=1)

    def test_folklore_is_refuted_not_repeated(self) -> None:
        result = blood.thermal(100.0, 42.0)
        self.assertLess(result["deficit_litres"], result["folklore_litres"])
        self.assertIn("not supported", result["folklore_verdict"])

    def test_range_brackets_the_point_estimate(self) -> None:
        result = blood.thermal(100.0, 42.0)
        low, high = result["deficit_range_litres"]
        self.assertLessEqual(low, result["deficit_litres"])
        self.assertGreaterEqual(high, result["deficit_litres"])

    def test_no_deficit_at_reference_temperature(self) -> None:
        result = blood.thermal(100.0, blood.REFERENCE_C)
        self.assertAlmostEqual(result["deficit_litres"], 0.0, places=2)

    def test_rejects_a_coefficient_outside_the_band(self) -> None:
        with self.assertRaises(ValueError):
            blood.thermal(100.0, 42.0, beta=0.5)

    def test_rejects_negative_volume(self) -> None:
        with self.assertRaises(ValueError):
            blood.thermal(-1.0, 42.0)


class TestDna(unittest.TestCase):
    def setUp(self) -> None:
        self.town = allocator.load_town()
        self.ledger = blood.build_dna(self.town)

    def test_ten_lots_of_ten_litres(self) -> None:
        self.assertEqual(self.ledger["lot_count"], 10)
        self.assertAlmostEqual(self.ledger["total_litres"], 100.0, places=2)

    def test_split_is_heart_first(self) -> None:
        self.assertEqual(self.ledger["split"]["hospital"], 7)
        self.assertEqual(self.ledger["split"]["water_pump"], 3)

    def test_first_seven_lots_are_the_heart(self) -> None:
        destinations = [lot["destination"] for lot in self.ledger["lots"]]
        self.assertEqual(destinations[:7], ["hospital"] * 7)
        self.assertEqual(destinations[7:], ["water_pump"] * 3)

    def test_chain_verifies(self) -> None:
        result = blood.verify_dna(self.ledger)
        self.assertTrue(result["ok"])
        self.assertEqual(result["lots"], 10)

    def test_genesis_links_the_first_lot(self) -> None:
        self.assertEqual(self.ledger["lots"][0]["prev"], blood.GENESIS)

    def test_each_lot_links_to_the_one_before(self) -> None:
        lots = self.ledger["lots"]
        for previous, current in zip(lots, lots[1:]):
            self.assertEqual(current["prev"], previous["hash"])

    def test_tampering_is_detected_at_the_edited_lot(self) -> None:
        self.ledger["lots"][2]["litres"] = 12.0
        result = blood.verify_dna(self.ledger)
        self.assertFalse(result["ok"])
        self.assertEqual(result["at"], 3)

    def test_tampering_with_the_head_is_detected(self) -> None:
        self.ledger["head"] = "f" * 64
        self.assertFalse(blood.verify_dna(self.ledger)["ok"])

    def test_mass_matches_volume(self) -> None:
        self.assertAlmostEqual(self.ledger["lots"][0]["mass_kg"], 8.35, places=3)

    def test_not_described_as_a_blockchain(self) -> None:
        self.assertIn("not a blockchain", self.ledger["note"])


class TestReconcile(unittest.TestCase):
    def setUp(self) -> None:
        self.town = allocator.load_town()
        self.ledger = blood.build_dna(self.town)

    def test_full_scan_reconciles(self) -> None:
        report = blood.reconcile(self.ledger, {"hospital": 70, "water_pump": 30})
        self.assertEqual(report["status"], "RECONCILED")
        self.assertEqual(report["missing_lots"], [])
        self.assertTrue(report["chain_ok"])

    def test_ten_litre_shortfall_names_lot_seven(self) -> None:
        report = blood.reconcile(self.ledger, shortfall_litres=10)
        self.assertEqual(report["status"], "SHORTFALL")
        self.assertEqual(report["missing_lots"], [7])
        self.assertAlmostEqual(report["organs"]["hospital"]["missing_litres"], 10.0)

    def test_shortfall_does_not_blame_the_pump(self) -> None:
        report = blood.reconcile(self.ledger, shortfall_litres=10)
        self.assertEqual(report["organs"]["water_pump"]["status"], "OK")

    def test_no_scan_is_not_a_pass(self) -> None:
        self.assertEqual(blood.reconcile(self.ledger)["status"], "NO_SCAN")

    def test_shortfall_is_evidence_not_accusation(self) -> None:
        report = blood.reconcile(self.ledger, shortfall_litres=10)
        self.assertIn("not evidence of who", report["note"])


class TestClock(unittest.TestCase):
    def setUp(self) -> None:
        self.town = allocator.load_town()

    def test_seventy_litres_is_four_hours(self) -> None:
        clock = blood.death_clock(self.town, 70.0)
        self.assertEqual(clock["minutes"], 240)
        self.assertEqual(clock["label"], "4 h 00 m")

    def test_load_shortens_the_clock(self) -> None:
        clock = blood.death_clock(self.town, 70.0, load=1.2)
        self.assertEqual(clock["minutes"], 200)
        self.assertEqual(clock["label"], "3 h 20 m")

    def test_empty_tank_dies_now(self) -> None:
        clock = blood.death_clock(self.town, 0.0)
        self.assertEqual(clock["minutes"], 0)

    def test_load_bounds_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            blood.death_clock(self.town, 70.0, load=0.1)
        with self.assertRaises(ValueError):
            blood.death_clock(self.town, 70.0, load=3.0)

    def test_it_does_not_claim_to_predict_failure(self) -> None:
        clock = blood.death_clock(self.town, 70.0)
        self.assertEqual(clock["confidence"], "arithmetic")
        self.assertIn("not a failure prediction", clock["note"])


class TestInverse(unittest.TestCase):
    def setUp(self) -> None:
        self.town = allocator.load_town()
        self.inverse = blood.inverse(self.town)

    def test_heart_is_four_hours(self) -> None:
        self.assertEqual(self.inverse["heart"]["label"], "4 h 00 m")
        self.assertEqual(self.inverse["heart"]["litres"], 70.0)

    def test_lungs_are_six_hours(self) -> None:
        self.assertEqual(self.inverse["lungs"]["label"], "6 h 00 m")

    def test_water_reaches_two_days(self) -> None:
        self.assertAlmostEqual(self.inverse["water"]["litres_delivered"], 24000.0)
        self.assertAlmostEqual(self.inverse["water"]["days_at_documented_demand"], 2.0)

    def test_naive_split_costs_fifty_minutes_of_heart(self) -> None:
        self.assertEqual(self.inverse["naive_split"]["heart_label"], "2 h 51 m")

    def test_hours_are_derived_from_burn_rate(self) -> None:
        self.assertAlmostEqual(
            self.inverse["heart"]["hours"],
            70 / self.town["organs"]["hospital"]["generator_l_per_hour"],
            places=2,
        )


class TestBundle(unittest.TestCase):
    def test_build_is_consistent(self) -> None:
        payload = blood.build(allocator.load_town())
        self.assertEqual(payload["allocation"], {"hospital": 70, "water_pump": 30})
        self.assertTrue(payload["dna_verify"]["ok"])
        self.assertEqual(payload["inverse"]["heart"]["litres"], 70)
        self.assertAlmostEqual(payload["sweat"]["litres_at_reference"], 97.78, places=2)

    def test_every_claim_carries_its_limit(self) -> None:
        payload = blood.build(allocator.load_town())
        self.assertEqual(len(payload["honesty"]), 4)
        for line in payload["honesty"]:
            self.assertTrue(line.strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
