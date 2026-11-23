import threading
from collections import defaultdict

from models.driver import Driver
from models.exceptions import ValidationError, DuplicateError, NotFoundError, TripConflictError
from models.trip import Trip
from models.vehicle import Vehicle


def _check_unique(items, cls, key) -> set:
    seen = set()
    for item in items:
        if not isinstance(item, cls):
            raise ValidationError(f"Очікувався {cls.__name__}, отримано {type(item).__name__}.")
        k = key(item)
        if k in seen:
            raise DuplicateError(f"{cls.__name__}: значення {k} повторюється.")
        seen.add(k)
    return seen


def _check_references(trips, plates: set, driver_ids: set) -> None:
    for trip in trips:
        if trip.driver.driver_id not in driver_ids:
            raise NotFoundError(f"Поїздка {trip.trip_id}: водія {trip.driver.driver_id} немає в наборі.")
        if trip.vehicle.plate not in plates:
            raise NotFoundError(f"Поїздка {trip.trip_id}: автомобіля {trip.vehicle.plate} немає в наборі.")


def _check_conflicts(trips) -> None:
    """Шукає перетини поїздок одного водія або одного авто за O(n log n)."""
    groups = defaultdict(list)
    for trip in trips:
        groups["driver:" + trip.driver.driver_id].append(trip)
        groups["vehicle:" + trip.vehicle.plate].append(trip)
    for group in groups.values():
        group.sort(key=lambda t: t.start)
        for current, following in zip(group, group[1:]):
            if following.start <= current.end:
                raise TripConflictError(f"Поїздка {following.trip_id} конфліктує з поїздкою {current.trip_id}.")


class FleetModel:
    def __init__(self):
        self._vehicles = []
        self._drivers = []
        self._trips = []
        self._lock = threading.Lock()

    @property
    def vehicles(self) -> tuple:
        with self._lock:
            return tuple(self._vehicles)

    @property
    def drivers(self) -> tuple:
        with self._lock:
            return tuple(self._drivers)

    @property
    def trips(self) -> tuple:
        with self._lock:
            return tuple(self._trips)

    def add_vehicle(self, vehicle: Vehicle) -> None:
        if not isinstance(vehicle, Vehicle):
            raise ValidationError("Можна додати лише транспортний засіб.")
        with self._lock:
            if any(v.plate == vehicle.plate for v in self._vehicles):
                raise DuplicateError(f"Номер {vehicle.plate} вже зайнятий.")
            self._vehicles.append(vehicle)

    def find_by_plate(self, text):
        query = text.strip().upper()
        with self._lock:
            found = []
            for v in self._vehicles:
                if query in v.plate:
                    found.append(v)
            return found

    def add_driver(self, driver: Driver) -> None:
        if not isinstance(driver, Driver):
            raise ValidationError("Можна додати лише водія.")
        with self._lock:
            if any(d.driver_id == driver.driver_id for d in self._drivers):
                raise DuplicateError(f"ID {driver.driver_id} вже зайнято.")
            self._drivers.append(driver)

    def replace_all(self, vehicles, drivers, trips) -> None:
        """Замінює весь набір. Якщо дані некоректні, модель лишається без змін."""
        plates = _check_unique(vehicles, Vehicle, lambda v: v.plate)
        driver_ids = _check_unique(drivers, Driver, lambda d: d.driver_id)
        _check_unique(trips, Trip, lambda t: t.trip_id)
        _check_references(trips, plates, driver_ids)
        _check_conflicts(trips)
        with self._lock:
            self._vehicles = list(vehicles)
            self._drivers = list(drivers)
            self._trips = list(trips)

    def _conflicts(self, trip):
        conflicts = []
        for t in self._trips:
            if trip.overlaps(t):
                conflicts.append(t)
        return conflicts

    def find_conflicts(self, trip):
        with self._lock:
            return self._conflicts(trip)

    def add_trip(self, trip: Trip) -> None:
        if not isinstance(trip, Trip):
            raise ValidationError("Можна додати лише поїздку.")
        with self._lock:
            if not any(d.driver_id == trip.driver.driver_id for d in self._drivers):
                raise NotFoundError(f"Водія {trip.driver.driver_id} немає в наборі.")
            if not any(v.plate == trip.vehicle.plate for v in self._vehicles):
                raise NotFoundError(f"Авто {trip.vehicle.plate} немає в наборі.")
            if any(t.trip_id == trip.trip_id for t in self._trips):
                raise DuplicateError(f"Поїздка з ID {trip.trip_id} вже існує.")
            conflicts = self._conflicts(trip)
            if conflicts:
                raise TripConflictError(f"Поїздка {trip.trip_id} перетинається в часі з поїздкою "
                                        f"{conflicts[0].trip_id} (той самий водій або авто).")
            self._trips.append(trip)

    def remove_trip(self, trip_id: str) -> None:
        with self._lock:
            for index, trip in enumerate(self._trips):
                if trip.trip_id == trip_id:
                    del self._trips[index]
                    return
        raise NotFoundError(f"Поїздку {trip_id} не знайдено.")

    def remove_driver(self, driver_id: str) -> None:
        with self._lock:
            if any(t.driver.driver_id == driver_id for t in self._trips):
                raise ValidationError(f"Водій {driver_id} має поїздки; спершу видаліть їх.")
            for index, driver in enumerate(self._drivers):
                if driver.driver_id == driver_id:
                    del self._drivers[index]
                    return
        raise NotFoundError(f"Водія {driver_id} не знайдено.")

    def remove_vehicle(self, plate: str) -> None:
        with self._lock:
            if any(t.vehicle.plate == plate for t in self._trips):
                raise ValidationError(f"Авто {plate} має поїздки; спершу видаліть їх.")
            for index, v in enumerate(self._vehicles):
                if v.plate == plate:
                    del self._vehicles[index]
                    return
        raise NotFoundError(f"Авто {plate} не знайдено.")

    def find_vehicle(self, plate: str) -> Vehicle:
        with self._lock:
            for v in self._vehicles:
                if v.plate == plate:
                    return v
        raise NotFoundError(f"Авто {plate} не знайдено.")

    def find_driver(self, driver_id: str) -> Driver:
        with self._lock:
            for d in self._drivers:
                if d.driver_id == driver_id:
                    return d
        raise NotFoundError(f"Водія {driver_id} не знайдено.")

    def update_vehicle(self, plate, brand, year, mileage, last_service) -> None:
        vehicle = self.find_vehicle(plate)
        #тимчасовий об'єкт, лише перевіряє всі значення разом
        type(vehicle)(plate, brand, year, mileage, last_service)
        with self._lock:
            vehicle.brand = brand
            vehicle.year = year
            vehicle.mileage = mileage
            vehicle.last_service = last_service

    # ШІ: Claude Code, Claude Opus 5.5 – каркас update_driver з пропусками (перевірка категорій поїздок); пропуски заповнив автор.
    def update_driver(self, driver_id, full_name, categories) -> None:
        driver = self.find_driver(driver_id)
        Driver(driver_id, full_name, categories)
        with self._lock:
            needed = set()
            for trip in self._trips:
                if trip.driver.driver_id == driver_id:
                    needed.add(trip.vehicle.required_category())
            if not needed <= frozenset(categories):
                raise ValidationError(f"Водій {driver_id} має поїздки, для яких потрібні категорії: "
                                      f"{', '.join(sorted(needed))}.")
            driver.full_name = full_name
            driver.categories = categories
