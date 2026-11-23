# ШІ: Claude Code, Claude Opus 5.5 – тести FleetController (відкриття файлу і пошук).
"""Перевірка контролера без вікна. Запуск: python -m unittest tests.test_controller"""
import tempfile
import unittest
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.exceptions import StorageError
from models.fleet import FleetModel

FLEET_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet.json"


class FleetControllerTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)

    def test_open_file_fills_model(self):
        self.controller.open_file(FLEET_JSON)
        self.assertGreater(len(self.model.vehicles), 0)
        self.assertEqual(len(self.controller.search_vehicles("")), len(self.model.vehicles))

    def test_search_uses_model(self):
        self.controller.open_file(FLEET_JSON)
        plate = self.model.vehicles[0].plate
        self.assertIn(self.model.vehicles[0], self.controller.search_vehicles(plate[2:6]))

    def test_broken_file_keeps_old_data(self):
        self.controller.open_file(FLEET_JSON)
        before = self.model.vehicles
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "broken.json"
            broken.write_text("{ broken", encoding="utf-8")
            with self.assertRaises(StorageError):
                self.controller.open_file(broken)
        self.assertEqual(self.model.vehicles, before)

    def test_open_loads_drivers_and_trips(self):
        self.controller.open_file(FLEET_JSON)
        self.assertGreater(len(self.model.drivers), 0)
        self.assertGreater(len(self.model.trips), 0)

    def test_save_and_open_again(self):
        self.controller.open_file(FLEET_JSON)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "saved.json"
            self.controller.save_file(path)
            other = FleetController(FleetModel())
            other.open_file(path)
        self.assertEqual(len(other.search_vehicles("")), len(self.model.vehicles))


if __name__ == "__main__":
    unittest.main()
