import re
from abc import ABC, abstractmethod
from datetime import timedelta, date
from models.serviceable import Serviceable
from models.exceptions import ValidationError

MIN_YEAR = 1950
# ШІ: Claude Code, Claude Opus 5.5 – регулярний вираз для номера.
PLATE_PATTERN = r"[АВЕІКМНОРСТХ]{2}\d{4}[АВЕІКМНОРСТХ]{2}"


class Vehicle(Serviceable, ABC):
    """Доменний клас ТЗ."""

    def __init__(self, plate, brand, year, mileage, last_service):
        self.plate = plate
        self.brand = brand
        self.year = year
        self.mileage = mileage
        self.last_service = last_service

    # ШІ: Claude Code, Claude Opus 5.5 – виправлення трьох методів ТО за попереднім кодом автора.
    def next_service_date(self) -> date:
        return self.last_service + timedelta(days=self.service_interval_days())

    def days_until_service(self, today: date) -> int:
        return (self.next_service_date() - today).days

    def is_service_due(self, today: date) -> bool:
        return self.days_until_service(today) <= 0

    @abstractmethod
    def fuel_rate(self) -> float:
        pass

    @abstractmethod
    def required_category(self) -> str:
        pass

    @property
    def mileage(self) -> int:
        return self._mileage

    @mileage.setter
    def mileage(self, value: int) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValidationError("Пробіг має бути цілим числом, не меншим за 0.")
        self._mileage = value

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, value: int) -> None:
        if not isinstance(value, int) or not MIN_YEAR <= value <= date.today().year + 1:
            raise ValidationError(f"Рік випуску має бути цілим числом від {MIN_YEAR} до {date.today().year + 1}.")
        self._year = value

    @property
    def brand(self) -> str:
        return self._brand

    @brand.setter
    def brand(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Марка не може бути порожньою.")
        self._brand = value.strip()

    @property
    def last_service(self) -> date:
        return self._last_service

    @last_service.setter
    def last_service(self, value: date) -> None:
        if not isinstance(value, date):
            raise ValidationError("Дата останнього ТО має бути датою.")
        self._last_service = value

    @property
    def plate(self) -> str:
        return self._plate

    @plate.setter
    def plate(self, value: str) -> None:
        if not isinstance(value, str) or re.fullmatch(PLATE_PATTERN, value) is None:
            raise ValidationError("Номер має формат ВН1234АА: дві літери, чотири цифри, дві літери (кирилицею).")
        self._plate = value


# ШІ: Claude Code, Claude Opus 5.5 – приклад класу Car; Truck і Bus автор написав за зразком.
class Car(Vehicle):
    def fuel_rate(self) -> float:
        return 8

    def required_category(self) -> str:
        return "B"

    def service_interval_days(self) -> int:
        return 365


class Truck(Vehicle):
    def fuel_rate(self) -> float:
        return 28

    def required_category(self) -> str:
        return "C"

    def service_interval_days(self) -> int:
        return 180


class Bus(Vehicle):
    def fuel_rate(self) -> float:
        return 22

    def required_category(self) -> str:
        return "D"

    def service_interval_days(self) -> int:
        return 120
