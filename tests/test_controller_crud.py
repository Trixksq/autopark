# ШІ: Claude Code, Claude Opus 5.5 – тести CRUD у FleetController (додавання, редагування, видалення з рядків форми).
"""CRUD через контролер: форма передає рядки, контролер їх перетворює і викликає модель.
Запуск: python -m unittest tests.test_controller_crud"""
import unittest
from datetime import date, datetime

from controllers.fleet_controller import FleetController
from models.driver import Driver
from models.exceptions import DuplicateError, NotFoundError, TripConflictError, ValidationError
from models.fleet import FleetModel
from models.trip import Trip
from models.vehicle import Car, Truck


class CrudTestCase(unittest.TestCase):
    """Невеликий набір: вантажівка з поїздкою, легковик без поїздок, водій C з поїздкою, водій B без."""

    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self.truck = Truck("ВН1234АА", "MAN", 2018, 150000, date(2026, 3, 1))
        self.car = Car("АА0001ВВ", "Skoda", 2020, 40000, date(2026, 1, 15))
        self.driver_c = Driver("D1", "Петренко Іван", ["B", "C"])
        self.driver_b = Driver("D2", "Коваль Олена", ["B"])
        self.trip = Trip("T1", self.driver_c, self.truck,
                         datetime(2026, 3, 10, 8, 0), datetime(2026, 3, 10, 12, 0), 120)
        for vehicle in (self.truck, self.car):
            self.model.add_vehicle(vehicle)
        for driver in (self.driver_c, self.driver_b):
            self.model.add_driver(driver)
        self.model.add_trip(self.trip)


class VehicleCrudTests(CrudTestCase):
    def test_add_vehicle_parses_form_strings(self):
        vehicle = self.controller.add_vehicle("Truck", "ВН5555КК", "Volvo", "2019", "98000", "05.02.2026")
        self.assertIsInstance(vehicle, Truck)
        self.assertEqual(vehicle.year, 2019)
        self.assertEqual(vehicle.mileage, 98000)
        self.assertEqual(vehicle.last_service, date(2026, 2, 5))
        self.assertIn(vehicle, self.model.vehicles)

    def test_add_vehicle_normalizes_plate(self):
        vehicle = self.controller.add_vehicle("Car", "  вн5555кк ", "Volvo", "2019", "98000", "05.02.2026")
        self.assertEqual(vehicle.plate, "ВН5555КК")

    def test_add_vehicle_bad_year(self):
        with self.assertRaises(ValidationError):
            self.controller.add_vehicle("Car", "ВН5555КК", "Volvo", "двадцять", "98000", "05.02.2026")
        self.assertEqual(len(self.model.vehicles), 2)

    def test_add_vehicle_bad_date(self):
        with self.assertRaises(ValidationError):
            self.controller.add_vehicle("Car", "ВН5555КК", "Volvo", "2019", "98000", "31.02.2026")

    def test_add_vehicle_unknown_type(self):
        with self.assertRaises(ValidationError):
            self.controller.add_vehicle("Plane", "ВН5555КК", "Boeing", "2019", "98000", "05.02.2026")

    def test_add_vehicle_duplicate(self):
        with self.assertRaises(DuplicateError):
            self.controller.add_vehicle("Car", "ВН1234АА", "Volvo", "2019", "98000", "05.02.2026")

    def test_update_vehicle(self):
        self.controller.update_vehicle("ВН1234АА", "MAN TGX", "2019", "151000", "01.04.2026")
        self.assertEqual(self.truck.brand, "MAN TGX")
        self.assertEqual(self.truck.year, 2019)
        self.assertEqual(self.truck.mileage, 151000)
        self.assertEqual(self.truck.last_service, date(2026, 4, 1))

    def test_update_vehicle_keeps_trip_reference(self):
        self.controller.update_vehicle("ВН1234АА", "MAN TGX", "2019", "151000", "01.04.2026")
        self.assertEqual(self.model.trips[0].vehicle.brand, "MAN TGX")

    def test_update_vehicle_all_or_nothing(self):
        with self.assertRaises(ValidationError):
            self.controller.update_vehicle("ВН1234АА", "Volvo", "2019", "-5", "01.04.2026")
        self.assertEqual(self.truck.brand, "MAN")
        self.assertEqual(self.truck.year, 2018)

    def test_update_unknown_vehicle(self):
        with self.assertRaises(NotFoundError):
            self.controller.update_vehicle("КА0000КА", "Volvo", "2019", "1000", "01.04.2026")

    def test_delete_vehicle(self):
        self.controller.delete_vehicle("АА0001ВВ")
        self.assertNotIn(self.car, self.model.vehicles)

    def test_delete_vehicle_with_trips(self):
        with self.assertRaises(ValidationError):
            self.controller.delete_vehicle("ВН1234АА")
        self.assertIn(self.truck, self.model.vehicles)

    def test_delete_unknown_vehicle(self):
        with self.assertRaises(NotFoundError):
            self.controller.delete_vehicle("КА0000КА")


class DriverCrudTests(CrudTestCase):
    def test_add_driver_parses_categories(self):
        driver = self.controller.add_driver("D3", "Шевченко Тарас", "b, c")
        self.assertEqual(driver.categories, frozenset({"B", "C"}))
        self.assertIn(driver, self.model.drivers)

    def test_add_driver_bad_category(self):
        with self.assertRaises(ValidationError):
            self.controller.add_driver("D3", "Шевченко Тарас", "B, Z")

    def test_add_driver_duplicate(self):
        with self.assertRaises(DuplicateError):
            self.controller.add_driver("D1", "Шевченко Тарас", "B")

    def test_update_driver(self):
        self.controller.update_driver("D2", "Коваль-Мельник Олена", "B, D")
        self.assertEqual(self.driver_b.full_name, "Коваль-Мельник Олена")
        self.assertEqual(self.driver_b.categories, frozenset({"B", "D"}))

    def test_update_driver_cannot_drop_used_category(self):
        with self.assertRaises(ValidationError):
            self.controller.update_driver("D1", "Петренко Іван", "B")
        self.assertEqual(self.driver_c.categories, frozenset({"B", "C"}))

    def test_update_unknown_driver(self):
        with self.assertRaises(NotFoundError):
            self.controller.update_driver("D99", "Хтось", "B")

    def test_delete_driver(self):
        self.controller.delete_driver("D2")
        self.assertNotIn(self.driver_b, self.model.drivers)

    def test_delete_driver_with_trips(self):
        with self.assertRaises(ValidationError):
            self.controller.delete_driver("D1")


class TripCrudTests(CrudTestCase):
    def test_add_trip_parses_form_strings(self):
        trip = self.controller.add_trip("T2", "D1", "ВН1234АА", "10.03.2026 13:00", "10.03.2026 18:30", "85.5")
        self.assertEqual(trip.start, datetime(2026, 3, 10, 13, 0))
        self.assertEqual(trip.end, datetime(2026, 3, 10, 18, 30))
        self.assertEqual(trip.distance_km, 85.5)
        self.assertIn(trip, self.model.trips)

    def test_add_trip_conflict(self):
        with self.assertRaises(TripConflictError):
            self.controller.add_trip("T2", "D1", "АА0001ВВ", "10.03.2026 11:00", "10.03.2026 15:00", "40")

    def test_add_trip_unknown_driver(self):
        with self.assertRaises(NotFoundError):
            self.controller.add_trip("T2", "D99", "ВН1234АА", "11.03.2026 08:00", "11.03.2026 12:00", "40")

    def test_add_trip_unknown_vehicle(self):
        with self.assertRaises(NotFoundError):
            self.controller.add_trip("T2", "D1", "КА0000КА", "11.03.2026 08:00", "11.03.2026 12:00", "40")

    def test_add_trip_bad_datetime(self):
        with self.assertRaises(ValidationError):
            self.controller.add_trip("T2", "D1", "ВН1234АА", "2026-03-11", "11.03.2026 12:00", "40")

    def test_add_trip_bad_distance(self):
        with self.assertRaises(ValidationError):
            self.controller.add_trip("T2", "D1", "ВН1234АА", "11.03.2026 08:00", "11.03.2026 12:00", "сорок")

    def test_add_trip_driver_without_category(self):
        with self.assertRaises(ValidationError):
            self.controller.add_trip("T2", "D2", "ВН1234АА", "11.03.2026 08:00", "11.03.2026 12:00", "40")

    def test_delete_trip(self):
        self.controller.delete_trip("T1")
        self.assertEqual(self.model.trips, ())

    def test_delete_unknown_trip(self):
        with self.assertRaises(NotFoundError):
            self.controller.delete_trip("T99")


if __name__ == "__main__":
    unittest.main()
