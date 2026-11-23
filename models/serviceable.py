from abc import ABC, abstractmethod
from datetime import date


class Serviceable(ABC):

    @abstractmethod
    def service_interval_days(self) -> int:
        """Повертає інтервал між ТО в днях."""

    @abstractmethod
    def next_service_date(self) -> date:
        """Повертає дату наступного ТО."""

    @abstractmethod
    def days_until_service(self, today) -> int:
        """Повертає кількість днів до наступного ТО."""

    @abstractmethod
    def is_service_due(self, today) -> bool:
        """Повертає булеве значення необхідності в ТО."""
