# ШІ: Claude Code, Claude Opus 5.5 – тести мінімальної FleetModel (транспорт).
"""Перевірка сховища транспорту. Запуск: python -m unittest tests.test_fleet_model"""
import unittest
from datetime import date

from models.exceptions import DuplicateError, ValidationError
from models.fleet import FleetModel
from models.vehicle import Bus, Car, Truck

LAST_SERVICE = date(2026, 5, 14)


class FleetModelVehicleTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.truck = Truck("ВН1234АА", "MAN", 2019, 182500, LAST_SERVICE)
        self.car = Car("АА0001ВВ", "Skoda", 2020, 40000, LAST_SERVICE)
        self.bus = Bus("ВІ1234КК", "Ataman", 2018, 300000, LAST_SERVICE)

    def test_new_model_is_empty(self):
        self.assertEqual(len(self.model.vehicles), 0)

    def test_add_vehicles_of_different_types(self):
        for vehicle in (self.truck, self.car, self.bus):
            self.model.add_vehicle(vehicle)
        self.assertEqual(list(self.model.vehicles), [self.truck, self.car, self.bus])

    def test_duplicate_plate_is_rejected(self):
        self.model.add_vehicle(self.truck)
        same_plate = Car("ВН1234АА", "Toyota", 2021, 0, LAST_SERVICE)
        with self.assertRaises(DuplicateError):
            self.model.add_vehicle(same_plate)
        self.assertEqual(len(self.model.vehicles), 1)

    def test_duplicate_error_is_validation_error(self):
        self.assertTrue(issubclass(DuplicateError, ValidationError))

    def test_only_vehicles_can_be_added(self):
        with self.assertRaises(ValidationError):
            self.model.add_vehicle("ВН1234АА")

    def test_vehicles_cannot_be_changed_from_outside(self):
        self.model.add_vehicle(self.truck)
        try:
            self.model.vehicles.append(self.car)
        except AttributeError:
            pass
        self.assertEqual(len(self.model.vehicles), 1)


class FleetModelSearchTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.truck = Truck("ВН1234АА", "MAN", 2019, 182500, LAST_SERVICE)
        self.car = Car("АА0001ВВ", "Skoda", 2020, 40000, LAST_SERVICE)
        for vehicle in (self.truck, self.car):
            self.model.add_vehicle(vehicle)

    def test_find_by_part_of_plate(self):
        self.assertEqual(self.model.find_vehicles("1234"), [self.truck])

    def test_find_ignores_case_and_spaces(self):
        self.assertEqual(self.model.find_vehicles("  вн12 "), [self.truck])

    def test_empty_query_returns_all(self):
        self.assertEqual(self.model.find_vehicles(""), [self.truck, self.car])

    def test_no_match_returns_empty_list(self):
        self.assertEqual(self.model.find_vehicles("9999"), [])


if __name__ == "__main__":
    unittest.main()
