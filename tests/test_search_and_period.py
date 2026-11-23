# ШІ: Claude Code, Claude Opus 5.5 – тести пошуку за маркою (п. 4.2) і XML-звіту за період (п. 2 завдання).
"""Перевірка search_vehicles, filter_trips_by_period і періоду в XML-звіті.
Запуск: python -m unittest tests.test_search_and_period"""
import shutil
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.driver import Driver
from models.exceptions import ValidationError
from models.fleet import FleetModel
from models.trip import Trip
from models.vehicle import Car, Truck
from services.calculations import filter_trips_by_period
from services.xml_report import build_mileage_report


class FleetTestCase(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self.truck = Truck("ВН1234АА", "Volvo", 2018, 150000, date(2026, 3, 1))
        self.car = Car("АА0001ВВ", "Škoda Octavia", 2020, 40000, date(2026, 1, 15))
        self.driver = Driver("D1", "Петренко Іван", ["B", "C"])
        for vehicle in (self.truck, self.car):
            self.model.add_vehicle(vehicle)
        self.model.add_driver(self.driver)
        self.trips = [
            Trip("T1", self.driver, self.truck, datetime(2026, 3, 1, 0, 0), datetime(2026, 3, 1, 4, 0), 100),
            Trip("T2", self.driver, self.truck, datetime(2026, 3, 15, 8, 0), datetime(2026, 3, 15, 12, 0), 200),
            Trip("T3", self.driver, self.truck, datetime(2026, 3, 31, 23, 0), datetime(2026, 4, 1, 2, 0), 400),
            Trip("T4", self.driver, self.car, datetime(2026, 4, 1, 8, 0), datetime(2026, 4, 1, 9, 0), 800),
        ]
        for trip in self.trips:
            self.model.add_trip(trip)


class SearchTests(FleetTestCase):
    def test_by_brand(self):
        self.assertEqual(self.controller.search_vehicles("Volvo"), [self.truck])

    def test_by_part_of_brand_any_case(self):
        self.assertEqual(self.controller.search_vehicles("  oCTa "), [self.car])

    def test_by_plate_still_works(self):
        self.assertEqual(self.controller.search_vehicles("вн12"), [self.truck])

    def test_nothing_found(self):
        self.assertEqual(self.controller.search_vehicles("Tesla"), [])


class PeriodFilterTests(FleetTestCase):
    def ids(self, date_from, date_to):
        return [t.trip_id for t in filter_trips_by_period(self.trips, date_from, date_to)]

    def test_bounds_are_inclusive_by_start_date(self):
        self.assertEqual(self.ids(date(2026, 3, 1), date(2026, 3, 31)), ["T1", "T2", "T3"])

    def test_single_day(self):
        self.assertEqual(self.ids(date(2026, 4, 1), date(2026, 4, 1)), ["T4"])

    def test_open_bounds(self):
        self.assertEqual(self.ids(None, None), ["T1", "T2", "T3", "T4"])
        self.assertEqual(self.ids(date(2026, 3, 16), None), ["T3", "T4"])
        self.assertEqual(self.ids(None, date(2026, 3, 1)), ["T1"])

    def test_empty_period(self):
        self.assertEqual(self.ids(date(2026, 5, 1), date(2026, 5, 31)), [])


class PeriodReportTests(FleetTestCase):
    def setUp(self):
        super().setUp()
        self.folder = Path(tempfile.mkdtemp())
        self.path = self.folder / "report.xml"

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def export(self, *period):
        thread = self.controller.export_xml_async(self.path, *period)
        self.assertIsInstance(thread, threading.Thread)
        while True:
            kind, payload = self.controller.events.get(timeout=10)
            if kind in ("done", "error"):
                thread.join(10)
                self.assertEqual(kind, "done", payload)
                return ET.parse(self.path).getroot()

    def test_root_has_period(self):
        root = build_mileage_report([], date(2026, 11, 23), date(2026, 3, 1), date(2026, 3, 31))
        self.assertEqual((root.get("period_from"), root.get("period_to")), ("2026-03-01", "2026-03-31"))

    def test_root_without_period(self):
        root = build_mileage_report([], date(2026, 11, 23))
        self.assertIsNone(root.get("period_from"))
        self.assertIsNone(root.get("period_to"))

    def test_export_counts_only_period(self):
        root = self.export("01.03.2026", "31.03.2026")
        self.assertEqual(root.get("period_from"), "2026-03-01")
        self.assertEqual(root.get("total_km"), "700.0")
        self.assertEqual(root.find("vehicle[@plate='ВН1234АА']").findtext("trips"), "3")
        self.assertEqual(root.find("vehicle[@plate='АА0001ВВ']").findtext("trips"), "0")

    def test_empty_strings_mean_all_trips(self):
        self.assertEqual(self.export("", "  ").get("total_km"), "1500.0")

    def test_bad_date_is_reported_before_thread(self):
        with self.assertRaises(ValidationError):
            self.controller.export_xml_async(self.path, "2026-03-01", "")
        self.assertFalse(self.path.exists())

    def test_from_after_to(self):
        with self.assertRaises(ValidationError):
            self.controller.export_xml_async(self.path, "02.03.2026", "01.03.2026")


if __name__ == "__main__":
    unittest.main()
