# ШІ: Claude Code, Claude Opus 5.5 – тести завантаження транспорту з JSON.
"""Перевірка читання JSON і обробки пошкоджених файлів. Запуск: python -m unittest tests.test_json_storage"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from models.exceptions import StorageError
from models.vehicle import Bus, Car, Truck, Vehicle
from services.json_storage import load_fleet, vehicle_from_dict

TRUCK = {"type": "Truck", "plate": "ВН1234АА", "brand": "MAN", "year": 2019,
         "mileage": 182500, "last_service": "2026-05-14"}


class VehicleFromDictTests(unittest.TestCase):
    def test_builds_right_class(self):
        truck = vehicle_from_dict(TRUCK)
        self.assertIsInstance(truck, Truck)
        self.assertEqual(truck.plate, "ВН1234АА")
        self.assertEqual(truck.last_service, date(2026, 5, 14))

    def test_each_type(self):
        for type_name, cls in (("Car", Car), ("Truck", Truck), ("Bus", Bus)):
            with self.subTest(type_name=type_name):
                self.assertIsInstance(vehicle_from_dict({**TRUCK, "type": type_name}), cls)

    def test_bad_records(self):
        bad = [
            {**TRUCK, "type": "Plane"},
            {key: value for key, value in TRUCK.items() if key != "year"},
            {**TRUCK, "year": 1800},
            {**TRUCK, "last_service": "14.05.2026"},
            {**TRUCK, "last_service": None},
            "not a dict",
        ]
        for record in bad:
            with self.subTest(record=record), self.assertRaises(StorageError):
                vehicle_from_dict(record)


class LoadErrorsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, text: str) -> Path:
        path = self.folder / "test.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_file(self):
        with self.assertRaises(StorageError):
            load_fleet(self.folder / "absent.json")

    def test_broken_json(self):
        with self.assertRaises(StorageError):
            load_fleet(self.write('{"vehicles": [ {"type": '))

    def test_wrong_structure(self):
        for text in ('[]', '{}', '{"vehicles": {}, "drivers": [], "trips": []}'):
            with self.subTest(text=text), self.assertRaises(StorageError):
                load_fleet(self.write(text))

    def test_one_bad_vehicle_rejects_file(self):
        data = {"vehicles": [TRUCK, {**TRUCK, "plate": "ВН12АА"}], "drivers": [], "trips": []}
        with self.assertRaises(StorageError) as context:
            load_fleet(self.write(json.dumps(data, ensure_ascii=False)))
        self.assertIn("2", str(context.exception))

    def test_empty_sections_are_allowed(self):
        loaded = load_fleet(self.write('{"vehicles": [], "drivers": [], "trips": []}'))
        self.assertEqual([list(part) for part in loaded], [[], [], []])
        self.assertTrue(all(isinstance(v, Vehicle) for v in loaded[0]))


if __name__ == "__main__":
    unittest.main()
