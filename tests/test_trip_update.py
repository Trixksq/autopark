# ШІ: Claude Code, Claude Opus 5.5 – тести редагування поїздки (п. 4.1 завдання).
"""Перевірка get_trip і update_trip у контролері та моделі. Запуск: python -m unittest tests.test_trip_update"""
import unittest
from datetime import date, datetime

from controllers.fleet_controller import FleetController
from models.driver import Driver
from models.exceptions import NotFoundError, TripConflictError, ValidationError
from models.fleet import FleetModel
from models.trip import Trip
from models.vehicle import Car, Truck


class TripUpdateTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self.truck = Truck("ВН1234АА", "MAN", 2018, 150000, date(2026, 3, 1))
        self.car = Car("АА0001ВВ", "Skoda", 2020, 40000, date(2026, 1, 15))
        self.driver = Driver("D1", "Петренко Іван", ["B", "C"])
        self.driver_b = Driver("D2", "Коваль Олена", ["B"])
        for vehicle in (self.truck, self.car):
            self.model.add_vehicle(vehicle)
        for driver in (self.driver, self.driver_b):
            self.model.add_driver(driver)
        self.first = Trip("T1", self.driver, self.truck, datetime(2026, 3, 10, 8), datetime(2026, 3, 10, 12), 120)
        self.second = Trip("T2", self.driver, self.truck, datetime(2026, 3, 10, 14), datetime(2026, 3, 10, 18), 90)
        self.model.add_trip(self.first)
        self.model.add_trip(self.second)

    def assert_unchanged(self):
        self.assertEqual(self.model.trips, (self.first, self.second))

    def test_get_trip(self):
        self.assertIs(self.controller.get_trip("T1"), self.first)

    def test_get_unknown_trip(self):
        with self.assertRaises(NotFoundError):
            self.controller.get_trip("T99")

    def test_update_changes_fields(self):
        trip = self.controller.update_trip("T1", "D2", "АА0001ВВ", "11.03.2026 09:00", "11.03.2026 10:30", "55.5")
        self.assertEqual((trip.driver, trip.vehicle), (self.driver_b, self.car))
        self.assertEqual(trip.start, datetime(2026, 3, 11, 9))
        self.assertEqual(trip.end, datetime(2026, 3, 11, 10, 30))
        self.assertEqual(trip.distance_km, 55.5)
        self.assertIs(self.controller.get_trip("T1"), trip)

    def test_update_keeps_count_and_order(self):
        self.controller.update_trip("T1", "D1", "ВН1234АА", "10.03.2026 08:00", "10.03.2026 12:00", "130")
        self.assertEqual([t.trip_id for t in self.model.trips], ["T1", "T2"])

    def test_trip_does_not_conflict_with_itself(self):
        self.controller.update_trip("T1", "D1", "ВН1234АА", "10.03.2026 09:00", "10.03.2026 13:00", "120")
        self.assertEqual(self.model.trips[0].end, datetime(2026, 3, 10, 13))

    def test_conflict_leaves_trip_unchanged(self):
        with self.assertRaises(TripConflictError):
            self.controller.update_trip("T1", "D1", "ВН1234АА", "10.03.2026 08:00", "10.03.2026 15:00", "120")
        self.assert_unchanged()

    def test_touching_boundary_is_conflict(self):
        with self.assertRaises(TripConflictError):
            self.controller.update_trip("T1", "D1", "ВН1234АА", "10.03.2026 08:00", "10.03.2026 14:00", "120")
        self.assert_unchanged()

    def test_one_minute_gap_is_allowed(self):
        self.controller.update_trip("T1", "D1", "ВН1234АА", "10.03.2026 08:00", "10.03.2026 13:59", "120")
        self.assertEqual(self.model.trips[0].end, datetime(2026, 3, 10, 13, 59))

    def test_unknown_trip(self):
        with self.assertRaises(NotFoundError):
            self.controller.update_trip("T99", "D1", "ВН1234АА", "12.03.2026 08:00", "12.03.2026 12:00", "120")
        self.assert_unchanged()

    def test_unknown_driver_or_vehicle(self):
        with self.assertRaises(NotFoundError):
            self.controller.update_trip("T1", "D99", "ВН1234АА", "12.03.2026 08:00", "12.03.2026 12:00", "120")
        with self.assertRaises(NotFoundError):
            self.controller.update_trip("T1", "D1", "КА0000КА", "12.03.2026 08:00", "12.03.2026 12:00", "120")
        self.assert_unchanged()

    def test_driver_without_category(self):
        with self.assertRaises(ValidationError):
            self.controller.update_trip("T1", "D2", "ВН1234АА", "12.03.2026 08:00", "12.03.2026 12:00", "120")
        self.assert_unchanged()


if __name__ == "__main__":
    unittest.main()
