# ШІ: Claude Code, Claude Opus 5.5 – тести списків водіїв/поїздок і фонового розрахунку в FleetController.
"""Перевірка list_drivers, list_trips і calculate_async. Запуск: python -m unittest tests.test_controller_calc"""
import threading
import unittest
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.fleet import FleetModel
from services.calculations import VehicleReport

FLEET_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet.json"
WAIT_SECONDS = 10


def collect_events(controller: FleetController) -> list:
    events = []
    while True:
        kind, payload = controller.events.get(timeout=WAIT_SECONDS)
        events.append((kind, payload))
        if kind in ("done", "error"):
            return events


class ControllerListsTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self.controller.open_file(FLEET_JSON)

    def test_list_drivers(self):
        self.assertEqual(self.controller.list_drivers(), self.model.drivers)

    def test_list_trips(self):
        self.assertEqual(self.controller.list_trips(), self.model.trips)


class CalculateAsyncTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self.controller.open_file(FLEET_JSON)

    def test_report_event(self):
        thread = self.controller.calculate_async(workers=4)
        self.assertIsInstance(thread, threading.Thread)
        events = collect_events(self.controller)
        thread.join(WAIT_SECONDS)
        kinds = [kind for kind, _ in events]
        self.assertEqual(kinds[-1], "done")
        self.assertIn("report", kinds)
        self.assertLess(kinds.index("report"), len(kinds) - 1)
        rows = next(payload for kind, payload in events if kind == "report")
        self.assertEqual(len(rows), len(self.model.vehicles))
        self.assertTrue(all(isinstance(row, VehicleReport) for row in rows))

    def test_progress_events(self):
        self.controller.calculate_async(workers=2)
        progress = [payload for kind, payload in collect_events(self.controller) if kind == "progress"]
        self.assertGreaterEqual(len(progress), 2)
        self.assertEqual(progress, sorted(progress))

    def test_bad_workers_reports_error(self):
        self.controller.calculate_async(workers=0)
        self.assertEqual(collect_events(self.controller)[-1][0], "error")


if __name__ == "__main__":
    unittest.main()
