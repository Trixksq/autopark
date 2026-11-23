# ШІ: Claude Code, Claude Opus 5.5 – тести водіїв, поїздок, конфліктів і видалення у FleetModel.
"""Перевірка CRUD водіїв і поїздок. Запуск: python -m unittest tests.test_fleet_trips"""
import unittest
from datetime import date, datetime, timedelta

from models.driver import Driver
from models.exceptions import DuplicateError, NotFoundError, TripConflictError, ValidationError
from models.fleet import FleetModel
from models.trip import Trip
from models.vehicle import Truck

LAST_SERVICE = date(2026, 5, 14)
START = datetime(2026, 10, 1, 8, 0)
END = datetime(2026, 10, 1, 12, 0)


class FleetTripsBase(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.truck_a = Truck("ВН1234АА", "MAN", 2019, 0, LAST_SERVICE)
        self.truck_b = Truck("ВН5678АА", "DAF", 2020, 0, LAST_SERVICE)
        self.driver_a = Driver("D001", "Петренко І. О.", ["B", "C"])
        self.driver_b = Driver("D002", "Коваль О. П.", ["B", "C"])
        for vehicle in (self.truck_a, self.truck_b):
            self.model.add_vehicle(vehicle)
        for driver in (self.driver_a, self.driver_b):
            self.model.add_driver(driver)
        self.trip = Trip("T1", self.driver_a, self.truck_a, START, END, 100)

    def trip_at(self, trip_id, driver, vehicle, shift_hours):
        shift = timedelta(hours=shift_hours)
        return Trip(trip_id, driver, vehicle, START + shift, END + shift, 100)


class DriverCrudTests(FleetTripsBase):
    def test_drivers_are_stored(self):
        self.assertEqual(list(self.model.drivers), [self.driver_a, self.driver_b])

    def test_duplicate_driver_id(self):
        with self.assertRaises(DuplicateError):
            self.model.add_driver(Driver("D001", "Інший І. І.", ["B"]))
        self.assertEqual(len(self.model.drivers), 2)

    def test_only_drivers_can_be_added(self):
        with self.assertRaises(ValidationError):
            self.model.add_driver("D003")


class TripCrudTests(FleetTripsBase):
    def test_add_trip(self):
        self.model.add_trip(self.trip)
        self.assertEqual(list(self.model.trips), [self.trip])

    def test_unknown_driver_or_vehicle(self):
        stranger = Driver("D999", "Чужий Ч. Ч.", ["C"])
        foreign_truck = Truck("АА0000АА", "Volvo", 2015, 0, LAST_SERVICE)
        for trip in (Trip("T2", stranger, self.truck_a, START, END, 100),
                     Trip("T3", self.driver_a, foreign_truck, START, END, 100)):
            with self.subTest(trip=trip.trip_id), self.assertRaises(NotFoundError):
                self.model.add_trip(trip)
        self.assertEqual(len(self.model.trips), 0)

    def test_duplicate_trip_id(self):
        self.model.add_trip(self.trip)
        with self.assertRaises(DuplicateError):
            self.model.add_trip(self.trip_at("T1", self.driver_b, self.truck_b, 24))

    def test_conflict_is_rejected(self):
        self.model.add_trip(self.trip)
        with self.assertRaises(TripConflictError):
            self.model.add_trip(self.trip_at("T2", self.driver_a, self.truck_b, 1))
        self.assertEqual(list(self.model.trips), [self.trip])

    def test_conflict_error_is_validation_error(self):
        self.assertTrue(issubclass(TripConflictError, ValidationError))
        self.assertTrue(issubclass(NotFoundError, ValidationError))

    def test_find_conflicts(self):
        self.model.add_trip(self.trip)
        self.model.add_trip(self.trip_at("T2", self.driver_b, self.truck_b, 0))
        candidate = self.trip_at("T3", self.driver_a, self.truck_b, 2)
        self.assertEqual({t.trip_id for t in self.model.find_conflicts(candidate)}, {"T1", "T2"})
        free = self.trip_at("T4", self.driver_a, self.truck_a, 24)
        self.assertEqual(self.model.find_conflicts(free), [])

    def test_remove_trip(self):
        self.model.add_trip(self.trip)
        self.model.remove_trip("T1")
        self.assertEqual(len(self.model.trips), 0)
        with self.assertRaises(NotFoundError):
            self.model.remove_trip("T1")


class RemoveWithIntegrityTests(FleetTripsBase):
    def test_vehicle_with_trips_cannot_be_removed(self):
        self.model.add_trip(self.trip)
        with self.assertRaises(ValidationError):
            self.model.remove_vehicle("ВН1234АА")
        self.assertEqual(len(self.model.vehicles), 2)

    def test_remove_free_vehicle(self):
        self.model.remove_vehicle("ВН5678АА")
        self.assertEqual(list(self.model.vehicles), [self.truck_a])
        with self.assertRaises(NotFoundError):
            self.model.remove_vehicle("ВН5678АА")

    def test_driver_with_trips_cannot_be_removed(self):
        self.model.add_trip(self.trip)
        with self.assertRaises(ValidationError):
            self.model.remove_driver("D001")
        self.assertEqual(len(self.model.drivers), 2)

    def test_remove_free_driver(self):
        self.model.remove_driver("D002")
        self.assertEqual(list(self.model.drivers), [self.driver_a])
        with self.assertRaises(NotFoundError):
            self.model.remove_driver("D002")


if __name__ == "__main__":
    unittest.main()
