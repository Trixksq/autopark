import json
from datetime import date, datetime

from models.trip import Trip
from models.vehicle import Vehicle, Car, Truck, Bus
from models.driver import Driver
from models.exceptions import StorageError, ValidationError

VEHICLE_TYPES = {"Car": Car, "Truck": Truck, "Bus": Bus}


def vehicle_from_dict(data: dict) -> Vehicle:
    """Створює Car, Truck, або Bus зі словника з JSON."""
    if not isinstance(data, dict):
        raise StorageError("Запис має бути об'єктом JSON.")
    try:
        vehicle_class = VEHICLE_TYPES[data["type"]]
        last_service = date.fromisoformat(data["last_service"])
        return vehicle_class(data["plate"], data["brand"], data["year"], data["mileage"], last_service)
    except KeyError as error:
        raise StorageError(f"Немає поля або невідомий тип: {error}") from error
    except ValueError as error:
        raise StorageError(f"Неправильний формат даних: {error}") from error
    except TypeError as error:
        raise StorageError(f"Неправильний тип значення: {error}") from error
    except ValidationError as error:
        raise StorageError(str(error)) from error


def driver_from_dict(data: dict) -> Driver:
    if not isinstance(data, dict):
        raise StorageError("Запис має бути об'єктом JSON.")
    try:
        return Driver(data["id"], data["full_name"], data["categories"])
    except KeyError as error:
        raise StorageError(f"Немає поля {error}") from error
    except ValidationError as error:
        raise StorageError(str(error)) from error


def trip_from_dict(data: dict, drivers: dict, vehicles: dict) -> Trip:
    if not isinstance(data, dict):
        raise StorageError("Запис має бути об'єктом JSON.")
    try:
        driver = drivers[data["driver_id"]]
        vehicle = vehicles[data["plate"]]
        start = datetime.fromisoformat(data["start"])
        end = datetime.fromisoformat(data["end"])
        return Trip(data["id"], driver, vehicle, start, end, data["distance_km"])
    except KeyError as error:
        raise StorageError(f"Немає поля або невідомий водій/авто: {error}") from error
    except ValueError as error:
        raise StorageError(f"Неправильний формат даних: {error}") from error
    except TypeError as error:
        raise StorageError(f"Неправильний формат даних: {error}") from error
    except ValidationError as error:
        raise StorageError(str(error)) from error


def load_fleet(path, progress=None) -> tuple:
    report = progress or (lambda value: None)
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except OSError as error:
        raise StorageError(f"Не вдалося відкрити файл: {error}") from error
    except json.JSONDecodeError as error:
        raise StorageError(f"Файл JSON пошкоджений: {error}") from error
    if not isinstance(data, dict):
        raise StorageError("Неправильна структура файлу JSON.")
    for section in ("vehicles", "drivers", "trips"):
        if not isinstance(data.get(section), list):
            raise StorageError(f"Розділ «{section}» має бути списком.")
    report(0.3)
    vehicles = []
    for number, item in enumerate(data["vehicles"], 1):
        try:
            vehicles.append(vehicle_from_dict(item))
        except StorageError as error:
            raise StorageError(f"Авто {number}: {error}") from error
    drivers = []
    for number, item in enumerate(data["drivers"], 1):
        try:
            drivers.append(driver_from_dict(item))
        except StorageError as error:
            raise StorageError(f"Водій {number}: {error}") from error
    report(0.5)
    trips = []
    drivers_by_id = {driver.driver_id: driver for driver in drivers}
    vehicles_by_plate = {vehicle.plate: vehicle for vehicle in vehicles}
    for number, item in enumerate(data["trips"], 1):
        try:
            trips.append(trip_from_dict(item, drivers_by_id, vehicles_by_plate))
        except StorageError as error:
            raise StorageError(f"Поїздка {number}: {error}") from error
        if number % 1000 == 0:
            report(0.5 + 0.5 * number / len(data["trips"]))
    report(1.0)
    return vehicles, drivers, trips


def vehicle_to_dict(vehicle: Vehicle) -> dict:
    return {
        "type": type(vehicle).__name__,
        "plate": vehicle.plate,
        "brand": vehicle.brand,
        "year": vehicle.year,
        "mileage": vehicle.mileage,
        "last_service": vehicle.last_service.isoformat(),
    }


def driver_to_dict(driver: Driver) -> dict:
    return {
        "id": driver.driver_id,
        "full_name": driver.full_name,
        "categories": sorted(driver.categories)
    }


def trip_to_dict(trip: Trip) -> dict:
    return {
        "id": trip.trip_id,
        "driver_id": trip.driver.driver_id,
        "plate": trip.vehicle.plate,
        "start": trip.start.isoformat(timespec="minutes"),
        "end": trip.end.isoformat(timespec="minutes"),
        "distance_km": trip.distance_km,
        "fuel_l": round(trip.fuel_l, 2)
    }


def save_fleet(path, vehicles, drivers, trips) -> None:
    data = {
        "vehicles": [vehicle_to_dict(v) for v in vehicles],
        "drivers": [driver_to_dict(d) for d in drivers],
        "trips": [trip_to_dict(t) for t in trips]
    }
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except OSError as error:
        raise StorageError(f"Не вдалося зберегти файл: {error}") from error
