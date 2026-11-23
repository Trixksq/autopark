# ШІ: Claude Code, Claude Opus 5.5 – тести класів Driver і Trip.
"""Перевірка водія, поїздки і конфлікту поїздок. Запуск: python -m unittest tests.test_driver_trip"""
import unittest
from datetime import date, datetime, timedelta

from models.driver import Driver
from models.exceptions import ValidationError
from models.trip import Trip
from models.vehicle import Bus, Car, Truck

LAST_SERVICE = date(2026, 5, 14)
START = datetime(2026, 10, 1, 8, 0)
END = datetime(2026, 10, 1, 12, 0)


class DriverTests(unittest.TestCase):
    def test_valid_driver(self):
        driver = Driver("D001", "Петренко Іван Олегович", ["B", "C"])
        self.assertEqual(driver.driver_id, "D001")
        self.assertEqual(driver.full_name, "Петренко Іван Олегович")
        self.assertEqual(driver.categories, {"B", "C"})

    def test_duplicate_categories_are_merged(self):
        self.assertEqual(Driver("D001", "Петренко І. О.", ["B", "B"]).categories, {"B"})

    def test_has_category(self):
        driver = Driver("D001", "Петренко І. О.", ["B", "C"])
        self.assertTrue(driver.has_category("C"))
        self.assertFalse(driver.has_category("D"))

    def test_bad_values(self):
        cases = [
            ("", "Петренко І. О.", ["B"]),
            ("D001", "   ", ["B"]),
            ("D001", "Петренко І. О.", []),
            ("D001", "Петренко І. О.", ["X"]),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValidationError):
                Driver(*args)


class TripTests(unittest.TestCase):
    def setUp(self):
        self.driver = Driver("D001", "Петренко І. О.", ["B", "C"])
        self.truck = Truck("ВН1234АА", "MAN", 2019, 182500, LAST_SERVICE)

    def make_trip(self, trip_id="T1", driver=None, vehicle=None, start=START, end=END, km=320):
        return Trip(trip_id, driver or self.driver, vehicle or self.truck, start, end, km)

    def test_fuel_by_formula(self):
        self.assertAlmostEqual(self.make_trip().fuel_l, 89.6)

    def test_fuel_is_polymorphic(self):
        car = Car("АА0001ВВ", "Skoda", 2020, 0, LAST_SERVICE)
        self.assertAlmostEqual(self.make_trip(vehicle=car, km=100).fuel_l, 8)

    def test_end_must_be_after_start(self):
        for end in (START, START - timedelta(minutes=1)):
            with self.subTest(end=end), self.assertRaises(ValidationError):
                self.make_trip(end=end)

    def test_distance_must_be_positive(self):
        for km in (0, -5):
            with self.subTest(km=km), self.assertRaises(ValidationError):
                self.make_trip(km=km)

    def test_driver_needs_vehicle_category(self):
        bus = Bus("ВІ0001КК", "Ataman", 2018, 0, LAST_SERVICE)
        with self.assertRaises(ValidationError):
            self.make_trip(vehicle=bus)


class OverlapTests(unittest.TestCase):
    def setUp(self):
        self.driver_a = Driver("D001", "Петренко І. О.", ["B", "C"])
        self.driver_b = Driver("D002", "Коваль О. П.", ["B", "C"])
        self.truck_a = Truck("ВН1234АА", "MAN", 2019, 0, LAST_SERVICE)
        self.truck_b = Truck("ВН5678АА", "DAF", 2020, 0, LAST_SERVICE)
        self.base = Trip("T1", self.driver_a, self.truck_a, START, END, 100)

    def other(self, driver, truck, start, end, trip_id="T2"):
        return Trip(trip_id, driver, truck, start, end, 100)

    def test_same_driver_overlap(self):
        trip = self.other(self.driver_a, self.truck_b, START + timedelta(hours=1), END + timedelta(hours=1))
        self.assertTrue(self.base.overlaps(trip))
        self.assertTrue(trip.overlaps(self.base))

    def test_same_vehicle_overlap(self):
        trip = self.other(self.driver_b, self.truck_a, START - timedelta(hours=1), START + timedelta(hours=1))
        self.assertTrue(self.base.overlaps(trip))

    def test_touching_boundary_is_conflict(self):
        trip = self.other(self.driver_a, self.truck_b, END, END + timedelta(hours=2))
        self.assertTrue(self.base.overlaps(trip))

    def test_gap_is_not_conflict(self):
        later = END + timedelta(minutes=1)
        trip = self.other(self.driver_a, self.truck_a, later, later + timedelta(hours=2))
        self.assertFalse(self.base.overlaps(trip))

    def test_other_driver_and_vehicle_is_not_conflict(self):
        trip = self.other(self.driver_b, self.truck_b, START, END)
        self.assertFalse(self.base.overlaps(trip))

    def test_trip_does_not_conflict_with_itself(self):
        edited = self.other(self.driver_a, self.truck_a, START, END, trip_id="T1")
        self.assertFalse(self.base.overlaps(edited))


if __name__ == "__main__":
    unittest.main()
