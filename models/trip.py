from datetime import datetime

from models.driver import Driver
from models.exceptions import ValidationError
from models.vehicle import Vehicle


class Trip:
    """Поїздка водія на транспортному засобі."""

    def __init__(self, trip_id, driver, vehicle, start, end, distance_km):
        if not isinstance(trip_id, str) or len(trip_id.strip()) == 0:
            raise ValidationError("ID поїздки не може бути порожнім.")
        self._trip_id = trip_id.strip()
        if not isinstance(driver, Driver):
            raise ValidationError("Неправильний водій.")
        self._driver = driver
        if not isinstance(vehicle, Vehicle):
            raise ValidationError("Неправильний транспортний засіб.")
        self._vehicle = vehicle
        if not isinstance(start, datetime):
            raise ValidationError("Неправильне значення для початку поїздки.")
        self._start = start
        if not isinstance(end, datetime):
            raise ValidationError("Неправильне значення для кінця поїздки.")
        self._end = end
        if end <= start:
            raise ValidationError("Кінець поїздки має бути пізніше за початок.")
        if not isinstance(distance_km, (int, float)) or distance_km <= 0:
            raise ValidationError("Відстань має бути числом, більшим за 0.")
        self._distance_km = distance_km
        if not driver.has_category(vehicle.required_category()):
            raise ValidationError(f"Водій {driver.driver_id} не має категорії {vehicle.required_category()} "
                                  f"для авто {vehicle.plate}.")

    @property
    def trip_id(self) -> str:
        return self._trip_id

    @property
    def driver(self) -> Driver:
        return self._driver

    @property
    def vehicle(self) -> Vehicle:
        return self._vehicle

    @property
    def start(self) -> datetime:
        return self._start

    @property
    def end(self) -> datetime:
        return self._end

    @property
    def distance_km(self) -> float:
        return self._distance_km

    @property
    def fuel_l(self) -> float:
        return self.vehicle.fuel_rate() * self._distance_km / 100

    def overlaps(self, other: "Trip") -> bool:
        if self.trip_id == other.trip_id:
            return False
        same_driver = self._driver.driver_id == other.driver.driver_id
        same_vehicle = self.vehicle.plate == other.vehicle.plate
        if not same_driver and not same_vehicle:
            return False
        return self.start <= other.end and other.start <= self.end
