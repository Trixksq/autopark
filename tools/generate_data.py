# ШІ: Claude Code, Claude Opus 5.5 – генератор тестових даних fleet.json і великого набору поїздок.
"""Генерує тестовий набір автопарку у форматі з DESIGN.md.

Запуск з кореня проєкту:
    python tools/generate_data.py                      -> data/fleet.json (75 записів)
    python tools/generate_data.py --big                -> data/fleet_big.json (10 000+ поїздок)
    python tools/generate_data.py --big --trips 500000 --out fleet_huge.json  -> для показу прогрес-бару

Кожен водій має «свій» автомобіль і щодня робить не більше однієї поїздки,
тому згенеровані поїздки не конфліктують між собою.
"""
import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLATE_LETTERS = "АВЕІКМНОРСТХ"
REGIONS = ["ВН", "АА", "ВІ", "АХ", "ВС", "КА"]
BRANDS = {
    "Car": ["Skoda", "Toyota", "Renault", "Volkswagen", "Hyundai"],
    "Truck": ["MAN", "DAF", "Volvo", "Scania", "Iveco"],
    "Bus": ["Ataman", "Mercedes-Benz", "Iveco", "Setra"],
}
TYPE_WEIGHTS = {"Car": 3, "Truck": 5, "Bus": 2}
CATEGORY = {"Car": "B", "Truck": "C", "Bus": "D"}
FUEL_RATE = {"Car": 8, "Truck": 28, "Bus": 22}
KM_PER_YEAR = {"Car": (10_000, 25_000), "Truck": (60_000, 120_000), "Bus": (40_000, 80_000)}
LAST_NAMES = ["Петренко", "Коваль", "Шевчук", "Бондар", "Ткаченко", "Мельник", "Кравчук",
              "Савченко", "Руденко", "Лисенко", "Гончар", "Олійник", "Мороз", "Павленко"]
FIRST_NAMES = ["Іван", "Олег", "Андрій", "Сергій", "Микола", "Віктор", "Дмитро", "Юрій", "Петро"]
PATRONYMICS = ["Іванович", "Олегович", "Андрійович", "Сергійович", "Миколайович", "Петрович"]


def make_plate(rng: random.Random, used: set) -> str:
    while True:
        plate = rng.choice(REGIONS) + f"{rng.randint(0, 9999):04d}" + "".join(rng.choices(PLATE_LETTERS, k=2))
        if plate not in used:
            used.add(plate)
            return plate


def make_vehicles(rng: random.Random, count: int) -> list:
    types = rng.choices(list(TYPE_WEIGHTS), weights=list(TYPE_WEIGHTS.values()), k=count)
    used, vehicles = set(), []
    for vehicle_type in types:
        last_service = date(2025, 10, 1) + timedelta(days=rng.randint(0, 380))
        year = rng.randint(2005, 2025)
        vehicles.append({
            "type": vehicle_type,
            "plate": make_plate(rng, used),
            "brand": rng.choice(BRANDS[vehicle_type]),
            "year": year,
            "mileage": (2026 - year + 1) * rng.randint(*KM_PER_YEAR[vehicle_type]),
            "last_service": last_service.isoformat(),
        })
    return vehicles


def make_drivers(rng: random.Random, vehicles: list, count: int) -> list:
    drivers = []
    for index in range(count):
        categories = {"B"}
        if index < len(vehicles):
            categories.add(CATEGORY[vehicles[index]["type"]])
        if rng.random() < 0.3:
            categories.add(rng.choice(["C", "CE", "D"]))
        full_name = f"{rng.choice(LAST_NAMES)} {rng.choice(FIRST_NAMES)} {rng.choice(PATRONYMICS)}"
        drivers.append({"id": f"D{index + 1:03d}", "full_name": full_name, "categories": sorted(categories)})
    return drivers


def make_trips(rng: random.Random, vehicles: list, drivers: list, count: int, first_day: date) -> list:
    pairs = min(len(vehicles), len(drivers))
    trips = []
    for index in range(count):
        pair = index % pairs
        day = first_day + timedelta(days=index // pairs)
        start = datetime.combine(day, datetime.min.time()) + timedelta(hours=rng.randint(6, 10))
        hours = rng.randint(2, 9)
        distance = hours * rng.randint(45, 70)
        vehicle = vehicles[pair]
        trips.append({
            "id": f"T{index + 1:05d}",
            "driver_id": drivers[pair]["id"],
            "plate": vehicle["plate"],
            "start": start.isoformat(timespec="minutes"),
            "end": (start + timedelta(hours=hours)).isoformat(timespec="minutes"),
            "distance_km": distance,
            "fuel_l": round(FUEL_RATE[vehicle["type"]] * distance / 100, 2),
        })
    return trips


def generate(vehicle_count: int, driver_count: int, trip_count: int, seed: int) -> dict:
    rng = random.Random(seed)
    vehicles = make_vehicles(rng, vehicle_count)
    drivers = make_drivers(rng, vehicles, driver_count)
    trips = make_trips(rng, vehicles, drivers, trip_count, date(2026, 1, 5))
    return {"vehicles": vehicles, "drivers": drivers, "trips": trips}


def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор тестових даних автопарку")
    parser.add_argument("--big", action="store_true", help="великий набір для перевірки багатопоточності")
    parser.add_argument("--seed", type=int, default=14, help="зерно генератора для відтворюваності")
    parser.add_argument("--trips", type=int, help="власна кількість поїздок (разом з --big)")
    parser.add_argument("--out", help="ім'я файлу в папці data")
    args = parser.parse_args()

    if args.big:
        data, name = generate(60, 70, args.trips or 12_000, args.seed), "fleet_big.json"
    else:
        data, name = generate(20, 15, args.trips or 40, args.seed), "fleet.json"
    name = args.out or name

    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(items) for items in data.values())
    print(f"{path.name}: {len(data['vehicles'])} авто, {len(data['drivers'])} водіїв, "
          f"{len(data['trips'])} поїздок, разом {total} записів")


if __name__ == "__main__":
    main()
