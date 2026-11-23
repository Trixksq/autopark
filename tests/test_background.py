# ШІ: Claude Code, Claude Opus 5.5 – тести фонового завантаження і збереження через FleetController.
"""Перевірка потоків і черги подій без вікна. Запуск: python -m unittest tests.test_background"""
import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.fleet import FleetModel
from services.json_storage import load_fleet

FLEET_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet.json"
WAIT_SECONDS = 10


def collect_events(controller: FleetController) -> list:
    """Читає події з черги, доки не прийде 'done' або 'error' (як це робить вікно через after())."""
    events = []
    while True:
        kind, payload = controller.events.get(timeout=WAIT_SECONDS)
        events.append((kind, payload))
        if kind in ("done", "error"):
            return events


class LoadProgressTests(unittest.TestCase):
    def test_progress_callback(self):
        values = []
        load_fleet(FLEET_JSON, progress=values.append)
        self.assertGreaterEqual(len(values), 3)
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(0 <= value <= 1 for value in values))
        self.assertEqual(values[-1], 1)

    def test_progress_is_optional(self):
        self.assertEqual(len(load_fleet(FLEET_JSON)), 3)


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_events_is_queue(self):
        self.assertIsInstance(self.controller.events, queue.Queue)

    def test_open_in_background(self):
        thread = self.controller.open_file_async(FLEET_JSON)
        self.assertIsInstance(thread, threading.Thread)
        events = collect_events(self.controller)
        thread.join(WAIT_SECONDS)
        self.assertEqual(events[-1][0], "done")
        self.assertGreater(len(self.model.vehicles), 0)
        self.assertGreater(len(self.model.trips), 0)

    def test_progress_events(self):
        self.controller.open_file_async(FLEET_JSON)
        events = collect_events(self.controller)
        progress = [payload for kind, payload in events if kind == "progress"]
        self.assertGreaterEqual(len(progress), 3)
        self.assertEqual(progress, sorted(progress))

    def test_worker_is_not_main_thread(self):
        thread = self.controller.open_file_async(FLEET_JSON)
        self.assertIsNot(thread, threading.main_thread())
        collect_events(self.controller)

    def test_broken_file_reports_error(self):
        self.controller.open_file(FLEET_JSON)
        before = self.model.vehicles
        broken = self.folder / "broken.json"
        broken.write_text("{ broken", encoding="utf-8")
        self.controller.open_file_async(broken)
        kind, message = collect_events(self.controller)[-1]
        self.assertEqual(kind, "error")
        self.assertIsInstance(message, str)
        self.assertTrue(message)
        self.assertEqual(self.model.vehicles, before)

    def test_save_in_background(self):
        self.controller.open_file(FLEET_JSON)
        path = self.folder / "saved.json"
        thread = self.controller.save_file_async(path)
        events = collect_events(self.controller)
        thread.join(WAIT_SECONDS)
        self.assertEqual(events[-1][0], "done")
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["trips"]), len(self.model.trips))

    def test_save_error_is_reported(self):
        self.controller.save_file_async(self.folder)
        self.assertEqual(collect_events(self.controller)[-1][0], "error")


if __name__ == "__main__":
    unittest.main()
