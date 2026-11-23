from models.exceptions import ValidationError

CATEGORY_CHOICES = frozenset({"A1", "A", "B1", "B", "C1", "C", "D1", "D", "BE", "C1E", "CE", "D1E", "DE", "T"})


class Driver:
    """Водій з категоріями."""

    def __init__(self, driver_id, full_name, categories):
        if not isinstance(driver_id, str) or len(driver_id.strip()) == 0:
            raise ValidationError("ID водія не може бути порожнім.")
        self._driver_id = driver_id.strip()
        self.full_name = full_name
        self.categories = categories

    def has_category(self, category: str) -> bool:
        return category in self._categories

    @property
    def driver_id(self):
        """Повертає ID водія."""
        return self._driver_id

    @property
    def full_name(self):
        """Повертає ім'я водія."""
        return self._full_name

    @full_name.setter
    def full_name(self, value) -> None:
        if not isinstance(value, str) or len(value.strip()) == 0:
            raise ValidationError("ПІБ водія не може бути порожнім.")
        self._full_name = value.strip()

    @property
    def categories(self):
        """Повертає категорії водія."""
        return self._categories

    @categories.setter
    def categories(self, value) -> None:
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValidationError("Категорії мають бути списком.")
        categories = frozenset(value)
        if not categories:
            raise ValidationError("Вкажіть хоча б одну категорію.")
        if not categories <= CATEGORY_CHOICES:
            wrong = categories - CATEGORY_CHOICES
            raise ValidationError(f"Недозволені категорії: {', '.join(sorted(wrong))}. "
                                  f"Дозволено: {', '.join(sorted(CATEGORY_CHOICES))}.")
        self._categories = categories
