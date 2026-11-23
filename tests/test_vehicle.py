# ШІ: Claude Code, Claude Opus 5.5 – тести класів Serviceable, Vehicle, Car, Truck, Bus.
"""Перевірка доменних класів транспорту. Запуск: python -m unittest tests.test_vehicle"""
import unittest
from datetime import date

from models.exceptions import ValidationError
from models.serviceable import Serviceable
from models.vehicle import Bus, Car, Truck, Vehicle

LAST_SERVICE = date(2026, 5, 14)


def make_truck(plate="ВН1234АА", brand="MAN", year=2019, mileage=182500):
    return Truck(plate, brand, year, mileage, LAST_SERVICE)


class HierarchyTests(unittest.TestCase):
    def test_vehicle_is_abstract(self):
        with self.assertRaises(TypeError):
            Vehicle("ВН1234АА", "MAN", 2019, 0, LAST_SERVICE)

    def test_serviceable_is_abstract(self):
        with self.assertRaises(TypeError):
            Serviceable()

    def test_vehicle_implements_serviceable(self):
        self.assertTrue(issubclass(Vehicle, Serviceable))

    def test_fuel_rate_is_polymorphic(self):
        fleet = [cls("ВН1234АА", "Марка", 2019, 0, LAST_SERVICE) for cls in (Car, Truck, Bus)]
        self.assertEqual([v.fuel_rate() for v in fleet], [8, 28, 22])
        self.assertEqual([v.required_category() for v in fleet], ["B", "C", "D"])
        self.assertEqual([v.service_interval_days() for v in fleet], [365, 180, 120])


class ValidationTests(unittest.TestCase):
    def test_valid_vehicle_keeps_values(self):
        truck = make_truck()
        self.assertEqual(truck.plate, "ВН1234АА")
        self.assertEqual(truck.brand, "MAN")
        self.assertEqual(truck.year, 2019)
        self.assertEqual(truck.mileage, 182500)
        self.assertEqual(truck. last_service, LAST_SERVICE)

    def test_bad_plate(self):
        for plate in ("", "123", "ВН12АА", "ВН12345АА", "1234ВНАА"):
            with self.subTest(plate=plate), self.assertRaises(ValidationError):
                make_truck(plate=plate)

    def test_empty_brand(self):
        for brand in ("", "   "):
            with self.subTest(brand=brand), self.assertRaises(ValidationError):
                make_truck(brand=brand)

    def test_year_limits(self):
        next_year = date.today().year + 1
        self.assertEqual(make_truck(year=1950).year, 1950)
        self.assertEqual(make_truck(year=next_year).year, next_year)
        for year in (1949, next_year + 1):
            with self.subTest(year=year), self.assertRaises(ValidationError):
                make_truck(year=year)

    def test_mileage_limits(self):
        self.assertEqual(make_truck(mileage=0).mileage, 0)
        with self.assertRaises(ValidationError):
            make_truck(mileage=-1)

    def test_mileage_setter_validates(self):
        truck = make_truck()
        truck.mileage = 200000
        self.assertEqual(truck.mileage, 200000)
        with self.assertRaises(ValidationError):
            truck.mileage = -5
        self.assertEqual(truck.mileage, 200000)


class ServiceDateTests(unittest.TestCase):
    def setUp(self):
        self.truck = make_truck()

    def test_next_service_date(self):
        self.assertEqual(self.truck.next_service_date(), date(2026, 11, 10))

    def test_days_until_service(self):
        self.assertEqual(self.truck.days_until_service(date(2026, 11, 5)), 5)
        self.assertEqual(self.truck.days_until_service(date(2026, 11, 12)), -2)

    def test_service_due_limits(self):
        self.assertFalse(self.truck.is_service_due(date(2026, 11, 9)))
        self.assertTrue(self.truck.is_service_due(date(2026, 11, 10)))
        self.assertTrue(self.truck.is_service_due(date(2026, 11, 11)))


if __name__ == "__main__":
    unittest.main()
