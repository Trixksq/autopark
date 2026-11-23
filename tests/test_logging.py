# ШІ: Claude Code, Claude Opus 5.5 – тести логування: налаштування файлу журналу і записи контролера.
"""Перевірка services/logging_setup.py і журналу FleetController.
Запуск: python -m unittest tests.test_logging"""
import logging
import shutil
import tempfile
import unittest
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.fleet import FleetModel
from services.logging_setup import setup_logging

FLEET_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet.json"
CONTROLLER_LOGGER = "controllers.fleet_controller"


class SetupLoggingTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.handler = None

    def tearDown(self):
        if self.handler is not None:
            logging.getLogger().removeHandler(self.handler)
            self.handler.close()
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_writes_to_file(self):
        path = self.folder / "fleet.log"
        self.handler = setup_logging(path)
        logging.getLogger("test.logging").info("Перевірка журналу")
        self.handler.flush()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Перевірка журналу", text)
        self.assertIn("INFO", text)
        self.assertIn("MainThread", text)

    def test_creates_missing_folder(self):
        path = self.folder / "logs" / "fleet.log"
        self.handler = setup_logging(path)
        self.assertTrue(path.parent.is_dir())

    def test_returns_handler_attached_to_root(self):
        self.handler = setup_logging(self.folder / "fleet.log")
        self.assertIsInstance(self.handler, logging.Handler)
        self.assertIn(self.handler, logging.getLogger().handlers)
        self.assertLessEqual(logging.getLogger().level, logging.INFO)


class ControllerLoggingTests(unittest.TestCase):
    def setUp(self):
        self.model = FleetModel()
        self.controller = FleetController(self.model)

    def wait(self) -> str:
        while True:
            kind, _ = self.controller.events.get(timeout=10)
            if kind in ("done", "error"):
                return kind

    def test_open_success_is_logged(self):
        with self.assertLogs(CONTROLLER_LOGGER, level="INFO") as logs:
            self.controller.open_file_async(FLEET_JSON)
            self.assertEqual(self.wait(), "done")
        self.assertTrue(any("fleet.json" in line for line in logs.output))

    def test_open_failure_is_logged_as_warning_or_error(self):
        with self.assertLogs(CONTROLLER_LOGGER, level="WARNING") as logs:
            self.controller.open_file_async(Path("no_such_file.json"))
            self.assertEqual(self.wait(), "error")
        self.assertTrue(any("no_such_file.json" in line for line in logs.output))

    def test_crud_is_logged(self):
        self.controller.open_file(FLEET_JSON)
        with self.assertLogs(CONTROLLER_LOGGER, level="INFO") as logs:
            self.controller.add_vehicle("Car", "КА7777КА", "Opel", "2015", "1000", "01.02.2026")
            self.controller.delete_vehicle("КА7777КА")
        self.assertEqual(sum("КА7777КА" in line for line in logs.output), 2)


if __name__ == "__main__":
    unittest.main()
