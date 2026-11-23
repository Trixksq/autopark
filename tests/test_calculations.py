# ШІ: Claude Code, Claude Opus 5.5 – тести розрахунку пального і термінів ТО частинами в ThreadPoolExecutor.
"""Перевірка services/calculations.py. Запуск: python -m unittest tests.test_calculations"""
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from models.driver import Driver
from models.trip import Trip
from models.vehicle import Bus, Car, Truck
from services.calculations import calculate_report, split_into_chunks, summarize_chunk
from services.json_storage import load_fleet

DATA = Path(__file__).resolve().parent.parent / "data"
TODAY = date(2026, 11, 13)
START = datetime(2026, 10, 1, 8, 0)


class SplitTests(unittest.TestCase):
    def test_all_items_kept_in_order(self):
        items = list(range(10))
        chunks = split_into_chunks(items, 3)
        self.assertEqual([item for chunk in chunks for item in chunk], items)

    def test_chunk_count_and_balance(self):
        chunks = split_into_chunks(list(range(10)), 3)
        self.assertEqual(len(chunks), 3)
        sizes = [len(chunk) for chunk in chunks]
        self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_more_chunks_than_items(self):
        chunks = split_into_chunks([1, 2], 5)
        self.assertEqual([item for chunk in chunks for item in chunk], [1, 2])
        self.assertTrue(all(chunks))

    def test_empty(self):
        self.assertEqual(split_into_chunks([], 4), [])

    def test_bad_count(self):
        with self.assertRaises(ValueError):
            split_into_chunks([1, 2], 0)


class SmallFleetTests(unittest.TestCase):
    def setUp(self):
        last_service = date(2026, 5, 14)
        self.truck = Truck("ВН1234АА", "MAN", 2019, 0, last_service)
        self.car = Car("АА0001ВВ", "Skoda", 2020, 0, last_service)
        self.bus = Bus("ВІ1234КК", "Ataman", 2018, 0, last_service)
        driver = Driver("D001", "Петренко І. О.", ["B", "C", "D"])
        self.trips = [
            Trip("T1", driver, self.truck, START, START + timedelta(hours=2), 100),
            Trip("T2", driver, self.truck, START + timedelta(days=1), START + timedelta(days=1, hours=2), 50),
            Trip("T3", driver, self.car, START + timedelta(days=2), START + timedelta(days=2, hours=2), 200),
        ]
        self.vehicles = [self.truck, self.car, self.bus]

    def test_summarize_chunk(self):
        totals = summarize_chunk(self.trips)
        self.assertEqual(totals["ВН1234АА"][0], 2)
        self.assertEqual(totals["ВН1234АА"][1], 150)
        self.assertAlmostEqual(totals["ВН1234АА"][2], 42)
        self.assertNotIn("ВІ1234КК", totals)

    def test_report_values(self):
        report = calculate_report(self.vehicles, self.trips, TODAY)
        self.assertEqual([row.plate for row in report], ["ВН1234АА", "АА0001ВВ", "ВІ1234КК"])
        truck, car, bus = report
        self.assertEqual((truck.trips_count, truck.distance_km), (2, 150))
        self.assertAlmostEqual(truck.fuel_l, 42)
        self.assertAlmostEqual(car.fuel_l, 16)
        self.assertEqual((bus.trips_count, bus.distance_km, bus.fuel_l), (0, 0, 0))
        self.assertEqual(truck.next_service, date(2026, 11, 10))
        self.assertEqual(truck.days_until_service, -3)
        self.assertEqual(car.days_until_service, self.car.days_until_service(TODAY))

    def test_bad_workers(self):
        with self.assertRaises(ValueError):
            calculate_report(self.vehicles, self.trips, TODAY, workers=0)


class ParallelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = "fleet_big.json" if (DATA / "fleet_big.json").exists() else "fleet.json"
        cls.vehicles, _, cls.trips = load_fleet(DATA / name)

    def test_threads_give_same_result(self):
        single = calculate_report(self.vehicles, self.trips, TODAY, workers=1)
        for workers in (2, 4, 8):
            with self.subTest(workers=workers):
                parallel = calculate_report(self.vehicles, self.trips, TODAY, workers=workers)
                self.assertEqual([(r.plate, r.trips_count, r.distance_km) for r in parallel],
                                 [(r.plate, r.trips_count, r.distance_km) for r in single])
                for a, b in zip(parallel, single):
                    self.assertAlmostEqual(a.fuel_l, b.fuel_l, places=6)

    def test_totals_match_trips(self):
        report = calculate_report(self.vehicles, self.trips, TODAY, workers=4)
        self.assertEqual(sum(row.trips_count for row in report), len(self.trips))
        self.assertEqual(sum(row.distance_km for row in report), sum(t.distance_km for t in self.trips))

    def test_progress(self):
        values = []
        calculate_report(self.vehicles, self.trips, TODAY, workers=4, progress=values.append)
        self.assertGreaterEqual(len(values), 2)
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], 1)


if __name__ == "__main__":
    unittest.main()
