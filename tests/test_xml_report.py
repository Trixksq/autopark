# ШІ: Claude Code, Claude Opus 5.5 – тести XML-звіту про пробіг (ElementTree) і фонового експорту в контролері.
"""Перевірка services/xml_report.py і FleetController.export_xml_async.
Запуск: python -m unittest tests.test_xml_report"""
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.exceptions import StorageError
from models.fleet import FleetModel
from services.calculations import VehicleReport
from services.xml_report import build_mileage_report, save_mileage_report

FLEET_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet.json"
GENERATED = date(2026, 11, 18)
ROWS = [
    VehicleReport("ВН1234АА", 3, 420, 117.6, date(2026, 8, 28), -82),
    VehicleReport("АА0001ВВ", 0, 0, 0.0, date(2027, 1, 15), 58),
    VehicleReport("КА7777КА", 2, 150.5, 33.11, date(2026, 12, 1), 13),
]


class BuildReportTests(unittest.TestCase):
    def setUp(self):
        self.root = build_mileage_report(ROWS, GENERATED)

    def test_root_element(self):
        self.assertEqual(self.root.tag, "mileage_report")
        self.assertEqual(self.root.get("date"), "2026-11-18")
        self.assertEqual(self.root.get("vehicles"), "3")

    def test_totals(self):
        self.assertEqual(self.root.get("total_km"), "570.5")
        self.assertEqual(self.root.get("total_fuel_l"), "150.71")

    def test_one_vehicle_element_per_row(self):
        plates = [element.get("plate") for element in self.root.findall("vehicle")]
        self.assertEqual(plates, ["ВН1234АА", "АА0001ВВ", "КА7777КА"])

    def test_vehicle_children(self):
        vehicle = self.root.find("vehicle[@plate='ВН1234АА']")
        self.assertEqual(vehicle.findtext("trips"), "3")
        self.assertEqual(vehicle.findtext("distance_km"), "420.0")
        self.assertEqual(vehicle.findtext("fuel_l"), "117.60")
        self.assertEqual(vehicle.findtext("next_service"), "2026-08-28")
        self.assertEqual(vehicle.findtext("days_until_service"), "-82")

    def test_service_due_flag(self):
        flags = {element.get("plate"): element.get("service_due") for element in self.root.findall("vehicle")}
        self.assertEqual(flags, {"ВН1234АА": "true", "АА0001ВВ": "false", "КА7777КА": "false"})

    def test_empty_report(self):
        root = build_mileage_report([], GENERATED)
        self.assertEqual(root.get("vehicles"), "0")
        self.assertEqual(root.get("total_km"), "0.0")
        self.assertEqual(root.findall("vehicle"), [])


class SaveReportTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_round_trip(self):
        path = self.folder / "report.xml"
        save_mileage_report(path, ROWS, GENERATED)
        root = ET.parse(path).getroot()
        self.assertEqual(len(root.findall("vehicle")), 3)
        self.assertEqual(root.find("vehicle").get("plate"), "ВН1234АА")

    def test_utf8_declaration(self):
        path = self.folder / "report.xml"
        save_mileage_report(path, ROWS, GENERATED)
        first_line = path.read_bytes().splitlines()[0].decode("utf-8")
        self.assertIn("<?xml", first_line)
        self.assertIn("utf-8", first_line.lower())
        self.assertIn("ВН1234АА", path.read_text(encoding="utf-8"))

    def test_bad_path(self):
        with self.assertRaises(StorageError):
            save_mileage_report(self.folder / "missing" / "report.xml", ROWS, GENERATED)


class ExportAsyncTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self.controller.open_file(FLEET_JSON)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def collect(self) -> list:
        events = []
        while True:
            kind, payload = self.controller.events.get(timeout=10)
            events.append((kind, payload))
            if kind in ("done", "error"):
                return events

    def test_export_writes_file(self):
        path = self.folder / "report.xml"
        thread = self.controller.export_xml_async(path)
        events = self.collect()
        thread.join(10)
        self.assertEqual(events[-1][0], "done")
        root = ET.parse(path).getroot()
        self.assertEqual(len(root.findall("vehicle")), len(self.model.vehicles))
        self.assertEqual(root.get("date"), date.today().isoformat())

    def test_export_bad_path_reports_error(self):
        self.controller.export_xml_async(self.folder / "missing" / "report.xml")
        self.assertEqual(self.collect()[-1][0], "error")


if __name__ == "__main__":
    unittest.main()
