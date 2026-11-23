class ValidationError(Exception):
    """Некоректні дані доменної моделі."""


class DuplicateError(ValidationError):
    """Помилки дублікатів."""


class StorageError(Exception):
    """Помилка читання файлу."""


class NotFoundError(ValidationError):
    """Запис не знайдено: водія, авто чи поїздки."""


class TripConflictError(ValidationError):
    """Поїздка конфліктує з наявною."""
