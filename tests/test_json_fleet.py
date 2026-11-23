# ШІ: Claude Code, Claude Opus 5.5 – тести завантаження і збереження повного набору (транспорт, водії, поїздки).
"""Перевірка load_fleet і save_fleet. Запуск: python -m unittest tests.test_json_fleet"""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from models.driver import Driver
from models.exceptions import StorageError
from models.trip import Trip
from services.json_storage import driver_from_dict, load_fleet, save_fleet, trip_from_dict, vehicle_from_dict

FLEET_JSON = Path(__file__).resolve().parent.parent / "data" / "fleet.json"
TRUCK = {"type": "Truck", "plate": "ВН1234АА", "brand": "MAN", "year": 2019,
         "mileage": 182500, "last_service": "2026-05-14"}
DRIVER = {"id": "D001", "full_name": "Петренко Іван Олегович", "categories": ["B", "C"]}
TRIP = {"id": "T00001", "driver_id": "D001", "plate": "ВН1234АА", "start": "2026-10-01T08:00",
        "end": "2026-10-01T15:30", "distance_km": 320, "fuel_l": 89.6}


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.truck = vehicle_from_dict(TRUCK)
        self.driver = driver_from_dict(DRIVER)
        self.drivers = {self.driver.driver_id: self.driver}
        self.vehicles = {self.truck.plate: self.truck}

    def test_driver_from_dict(self):
        self.assertIsInstance(self.driver, Driver)
        self.assertEqual(self.driver.categories, {"B", "C"})

    def test_bad_driver(self):
        for record in ({**DRIVER, "categories": ["X"]}, {"id": "D001"}, ["D001"]):
            with self.subTest(record=record), self.assertRaises(StorageError):
                driver_from_dict(record)

    def test_trip_is_linked_to_objects(self):
        trip = trip_from_dict(TRIP, self.drivers, self.vehicles)
        self.assertIsInstance(trip, Trip)
        self.assertIs(trip.driver, self.driver)
        self.assertIs(trip.vehicle, self.truck)
        self.assertEqual(trip.start, datetime(2026, 10, 1, 8, 0))

    def test_bad_trip(self):
        bad = [
            {**TRIP, "driver_id": "D999"},
            {**TRIP, "plate": "АА0000АА"},
            {**TRIP, "end": "2026-10-01T07:00"},
            {**TRIP, "start": "вчора"},
            {key: value for key, value in TRIP.items() if key != "distance_km"},
        ]
        for record in bad:
            with self.subTest(record=record), self.assertRaises(StorageError):
                trip_from_dict(record, self.drivers, self.vehicles)


class FleetFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, data) -> Path:
        path = self.folder / "fleet.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_load_project_file(self):
        vehicles, drivers, trips = load_fleet(FLEET_JSON)
        raw = json.loads(FLEET_JSON.read_text(encoding="utf-8"))
        self.assertEqual((len(vehicles), len(drivers), len(trips)),
                         (len(raw["vehicles"]), len(raw["drivers"]), len(raw["trips"])))
        plates = {vehicle.plate: vehicle for vehicle in vehicles}
        self.assertIs(trips[0].vehicle, plates[raw["trips"][0]["plate"]])

    def test_missing_section(self):
        for data in ({"vehicles": [TRUCK], "drivers": [DRIVER]},
                     {"vehicles": [TRUCK], "drivers": {}, "trips": []}):
            with self.subTest(data=data), self.assertRaises(StorageError):
                load_fleet(self.write(data))

    def test_bad_trip_reports_number(self):
        data = {"vehicles": [TRUCK], "drivers": [DRIVER],
                "trips": [TRIP, {**TRIP, "id": "T00002", "driver_id": "D999"}]}
        with self.assertRaises(StorageError) as context:
            load_fleet(self.write(data))
        self.assertIn("2", str(context.exception))

    def test_save_and_load_back(self):
        vehicles, drivers, trips = load_fleet(FLEET_JSON)
        path = self.folder / "copy.json"
        save_fleet(path, vehicles, drivers, trips)
        vehicles2, drivers2, trips2 = load_fleet(path)
        self.assertEqual([v.plate for v in vehicles2], [v.plate for v in vehicles])
        self.assertEqual([d.driver_id for d in drivers2], [d.driver_id for d in drivers])
        self.assertEqual([(t.trip_id, t.start, t.end) for t in trips2],
                         [(t.trip_id, t.start, t.end) for t in trips])
        self.assertEqual(type(vehicles2[0]), type(vehicles[0]))

    def test_saved_file_format(self):
        vehicles, drivers, trips = load_fleet(FLEET_JSON)
        path = self.folder / "copy.json"
        save_fleet(path, vehicles, drivers, trips)
        saved = json.loads(path.read_text(encoding="utf-8"))
        original = json.loads(FLEET_JSON.read_text(encoding="utf-8"))
        self.assertEqual(saved["vehicles"][0], original["vehicles"][0])
        self.assertEqual(saved["drivers"][0]["id"], original["drivers"][0]["id"])
        self.assertEqual(saved["trips"][0]["start"], original["trips"][0]["start"])
        self.assertAlmostEqual(saved["trips"][0]["fuel_l"], original["trips"][0]["fuel_l"], places=2)

    def test_save_error(self):
        with self.assertRaises(StorageError):
            save_fleet(self.folder, [], [], [])


if __name__ == "__main__":
    unittest.main()
