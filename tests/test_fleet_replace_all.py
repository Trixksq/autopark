# ШІ: Claude Code, Claude Opus 5.5 – тести FleetModel.replace_all (цілісність набору, конфлікти, швидкість).
"""Перевірка заміни всього набору. Запуск: python -m unittest tests.test_fleet_replace_all"""
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from models.driver import Driver
from models.exceptions import DuplicateError, NotFoundError, TripConflictError, ValidationError
from models.fleet import FleetModel
from models.trip import Trip
from models.vehicle import Truck
from services.json_storage import load_fleet

BIG_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet_big.json"
LAST_SERVICE = date(2026, 5, 14)
START = datetime(2026, 10, 1, 8, 0)


class ReplaceAllTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.old_truck = Truck("ВІ0001КК", "Volvo", 2015, 0, LAST_SERVICE)
        self.model.add_vehicle(self.old_truck)
        self.truck_a = Truck("ВН1234АА", "MAN", 2019, 0, LAST_SERVICE)
        self.truck_b = Truck("ВН5678АА", "DAF", 2020, 0, LAST_SERVICE)
        self.driver_a = Driver("D001", "Петренко І. О.", ["C"])
        self.driver_b = Driver("D002", "Коваль О. П.", ["C"])

    def trip(self, trip_id, driver, vehicle, shift_hours):
        start = START + timedelta(hours=shift_hours)
        return Trip(trip_id, driver, vehicle, start, start + timedelta(hours=3), 100)

    def assert_old_data_kept(self):
        self.assertEqual(list(self.model.vehicles), [self.old_truck])
        self.assertEqual(self.model.drivers, ())
        self.assertEqual(self.model.trips, ())

    def test_replace_all(self):
        trips = [self.trip("T1", self.driver_a, self.truck_a, 0), self.trip("T2", self.driver_b, self.truck_b, 0)]
        self.model.replace_all([self.truck_a, self.truck_b], [self.driver_a, self.driver_b], trips)
        self.assertEqual(list(self.model.vehicles), [self.truck_a, self.truck_b])
        self.assertEqual(list(self.model.drivers), [self.driver_a, self.driver_b])
        self.assertEqual(list(self.model.trips), trips)

    def test_duplicates_are_rejected(self):
        twin_driver = Driver("D001", "Двійник Д. Д.", ["C"])
        cases = [
            ([self.truck_a, Truck("ВН1234АА", "DAF", 2020, 0, LAST_SERVICE)], [self.driver_a], []),
            ([self.truck_a], [self.driver_a, twin_driver], []),
            ([self.truck_a, self.truck_b], [self.driver_a, self.driver_b],
             [self.trip("T1", self.driver_a, self.truck_a, 0), self.trip("T1", self.driver_b, self.truck_b, 10)]),
        ]
        for vehicles, drivers, trips in cases:
            with self.subTest(vehicles=len(vehicles), drivers=len(drivers)), self.assertRaises(DuplicateError):
                self.model.replace_all(vehicles, drivers, trips)
            self.assert_old_data_kept()

    def test_trip_must_reference_new_data(self):
        trips = [self.trip("T1", self.driver_b, self.truck_a, 0)]
        with self.assertRaises(NotFoundError):
            self.model.replace_all([self.truck_a], [self.driver_a], trips)
        self.assert_old_data_kept()

    def test_conflicts_are_rejected(self):
        for second in (self.trip("T2", self.driver_a, self.truck_b, 2),
                       self.trip("T2", self.driver_b, self.truck_a, 3),
                       self.trip("T2", self.driver_a, self.truck_b, -10 + 0.5)):
            first = self.trip("T1", self.driver_a, self.truck_a, 0)
            with self.subTest(start=second.start), self.assertRaises(TripConflictError):
                self.model.replace_all([self.truck_a, self.truck_b], [self.driver_a, self.driver_b],
                                       [first, self.trip("T0", self.driver_a, self.truck_a, -10), second])
            self.assert_old_data_kept()

    def test_wrong_types(self):
        with self.assertRaises(ValidationError):
            self.model.replace_all([self.truck_a], ["D001"], [])
        self.assert_old_data_kept()

    @unittest.skipUnless(BIG_JSON.exists(), "немає data/fleet_big.json – запустіть tools/generate_data.py --big")
    def test_big_file_is_fast(self):
        vehicles, drivers, trips = load_fleet(BIG_JSON)
        started = time.perf_counter()
        self.model.replace_all(vehicles, drivers, trips)
        elapsed = time.perf_counter() - started
        self.assertEqual(len(self.model.trips), len(trips))
        self.assertLess(elapsed, 3, "перевірка конфліктів занадто повільна: порівнюйте лише сусідні поїздки")


if __name__ == "__main__":
    unittest.main()
