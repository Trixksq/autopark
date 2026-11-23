"""Контролер: перетворює дії користувача на виклики моделі й сервісів, фонові задачі шле в чергу подій."""
import logging
import queue
import threading
import time
from datetime import date, datetime

from models.driver import Driver
from models.exceptions import StorageError, ValidationError
from models.fleet import FleetModel
from models.trip import Trip
from services.calculations import calculate_report
from services.json_storage import VEHICLE_TYPES, load_fleet, save_fleet
from services.xml_report import save_mileage_report

GIL_YIELD_SECONDS = 0.001

logger = logging.getLogger(__name__)


# ШІ: Claude Code, Claude Opus 5.5 – приклад _parse_int; решту функцій розбору автор написав за зразком.
def _parse_int(text: str, field: str) -> int:
    """Перетворює рядок з форми на ціле число."""
    try:
        return int(text.strip())
    except ValueError as error:
        raise ValidationError(f"{field}: потрібне ціле число, отримано «{text}».") from error


def _parse_float(text: str, field: str) -> float:
    """Перетворює рядок з форми на число (ціле або дробове, через крапку)."""
    try:
        return float(text.strip())
    except ValueError as error:
        raise ValidationError(f"{field}: потрібне число (наприклад, 85.5), отримано «{text}».") from error


def _parse_date(text: str) -> date:
    """Перетворює рядок з форми на дату у форматі ДД.ММ.РРРР."""
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y").date()
    except ValueError as error:
        raise ValidationError(f"Дата «{text}» має бути у форматі ДД.ММ.РРРР.") from error


def _parse_datetime(text: str) -> datetime:
    """Перетворює рядок з форми на дату й час у форматі ДД.ММ.РРРР ГГ:ХХ."""
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y %H:%M")
    except ValueError as error:
        raise ValidationError(f"Час «{text}» має бути у форматі ДД.ММ.РРРР ГГ:ХХ.") from error


def _parse_categories(text: str) -> list:
    """Рядок «b, c» → список ["B", "C"]; чи існують такі категорії, перевіряє Driver."""
    parts = text.upper().split(",")
    categories = []
    for c in parts:
        if len(c.strip()) == 0:
            continue
        categories.append(c.strip())
    return categories


class FleetController:
    """Контролер (Controller): виконує дії користувача над моделлю."""

    def __init__(self, model: FleetModel):
        self._model = model
        self.events = queue.Queue()

    def open_file(self, path) -> None:
        """Синхронно завантажує набір із JSON (для тестів і консолі)."""
        self._model.replace_all(*load_fleet(path))

    def search_vehicles(self, text: str) -> list:
        """Авто, у номері яких є text."""
        return self._model.find_by_plate(text)

    def save_file(self, path) -> None:
        """Синхронно зберігає набір у JSON."""
        save_fleet(path, self._model.vehicles, self._model.drivers, self._model.trips)

    def open_file_async(self, path) -> threading.Thread:
        """Запускає завантаження у фоновому потоці; результат приходить подією в self.events."""
        thread = threading.Thread(target=self._open_worker, args=(path,), daemon=True)
        thread.start()
        return thread

    def save_file_async(self, path) -> threading.Thread:
        """Запускає збереження у фоновому потоці."""
        thread = threading.Thread(target=self._save_worker, args=(path,), daemon=True)
        thread.start()
        return thread

    def _open_worker(self, path) -> None:
        """У фоновому потоці відкриває файл."""
        try:
            vehicles, drivers, trips = load_fleet(path, progress=self._report_progress)
            self._model.replace_all(vehicles, drivers, trips)
            logger.info("Відкрито %s: %d авто, %d поїздок", path, len(vehicles), len(trips))
            self.events.put(("done", f"Завантажено {len(vehicles)} авто, {len(drivers)} водіїв, {len(trips)} поїздок."))
        except (StorageError, ValidationError) as error:
            self.events.put(("error", str(error)))
            logger.warning("Не вдалося відкрити %s: %s", path, error)
        except Exception as error:
            self.events.put(("error", f"Непередбачена помилка: {error}"))
            logger.exception("Непередбачена помилка при відкритті %s", path)

    def _save_worker(self, path) -> None:
        """У фоновому потоці зберігає файл."""
        try:
            self.events.put(("progress", 0))
            self.save_file(path)
            self.events.put(("progress", 1))
            self.events.put(("done",
                             f"Збережено {len(self._model.vehicles)} авто, "
                             f"{len(self._model.drivers)} водіїв, {len(self._model.trips)} поїздок."))
            logger.info("Збережено %s: %d авто, %d водіїв, %d поїздок", path, len(self._model.vehicles),
                        len(self._model.drivers), len(self._model.trips))
        except (StorageError, ValidationError) as error:
            self.events.put(("error", str(error)))
            logger.warning("Не вдалося зберегти %s: %s", path, error)
        except Exception as error:
            self.events.put(("error", f"Непередбачена помилка: {error}"))
            logger.exception("Непередбачена помилка при збереженні %s", path)

    def _report_progress(self, value: float) -> None:
        """Кладе прогрес у чергу і на мить відпускає GIL, щоб вікно встигло перемалюватися."""
        self.events.put(("progress", value))
        time.sleep(GIL_YIELD_SECONDS)

    def list_drivers(self) -> tuple:
        """Усі водії."""
        return self._model.drivers

    def list_trips(self) -> tuple:
        """Усі поїздки."""
        return self._model.trips

    def calculate_async(self, workers) -> threading.Thread:
        """Запускає розрахунок пального й ТО у фоновому потоці; рядки звіту приходять подією "report"."""
        thread = threading.Thread(target=self._calculate_worker, args=(workers,), daemon=True)
        thread.start()
        return thread

    def _calculate_worker(self, workers) -> None:
        """У фоновому потоці рахує звіт у workers потоках пулу."""
        try:
            rows = calculate_report(self._model.vehicles, self._model.trips, date.today(), workers=workers,
                                    progress=self._report_progress)
            self.events.put(("report", rows))
            self.events.put(("done", f"Розраховано {len(rows)} авто."))
            logger.info("Розраховано звіт: %d авто, %d потоків", len(rows), workers)
        except (ValueError, ValidationError) as error:  # ValueError – неправильна кількість потоків
            self.events.put(("error", str(error)))
            logger.warning("Розрахунок не виконано (%s потоків): %s", workers, error)
        except Exception as error:
            self.events.put(("error", f"Непередбачена помилка: {error}"))
            logger.exception("Непередбачена помилка розрахунку (%s потоків)", workers)

    # ШІ: Claude Code, Claude Opus 5.5 – каркаси методів CRUD (add/update/delete) з пропусками; пропуски заповнив автор.
    def add_vehicle(self, type_key, plate, brand, year, mileage, last_service):
        """Створює авто з рядків форми і додає в модель."""
        if type_key not in VEHICLE_TYPES:
            raise ValidationError(f"Невідомий тип транспорту: {type_key}.")
        vehicle_class = VEHICLE_TYPES[type_key]
        vehicle = vehicle_class(plate.strip().upper(), brand, _parse_int(year, "Рік"), _parse_int(mileage, "Пробіг"),
                                _parse_date(last_service))
        self._model.add_vehicle(vehicle)
        logger.info("Додано авто %s", vehicle.plate)
        return vehicle

    def update_vehicle(self, plate, brand, year, mileage, last_service) -> None:
        """Змінює марку, рік, пробіг і дату ТО існуючого авто."""
        self._model.update_vehicle(plate, brand, _parse_int(year, "Рік"), _parse_int(mileage, "Пробіг"),
                                   _parse_date(last_service))
        logger.info("Відредаговано авто %s", plate)

    def delete_vehicle(self, plate) -> None:
        """Видаляє авто без поїздок."""
        self._model.remove_vehicle(plate)
        logger.info("Видалено авто %s", plate)

    def add_driver(self, driver_id, full_name, categories):
        """Створює водія; категорії приходять рядком «B, C»."""
        driver = Driver(driver_id, full_name, _parse_categories(categories))
        self._model.add_driver(driver)
        logger.info("Додано водія %s", driver.driver_id)
        return driver

    def update_driver(self, driver_id, full_name, categories) -> None:
        """Змінює ПІБ і категорії водія; категорії приходять рядком «B, C»."""
        self._model.update_driver(driver_id, full_name, _parse_categories(categories))
        logger.info("Відредаговано водія %s", driver_id)

    def delete_driver(self, driver_id) -> None:
        """Видаляє водія без поїздок."""
        self._model.remove_driver(driver_id)
        logger.info("Видалено водія %s", driver_id)

    def add_trip(self, trip_id, driver_id, plate, start, end, distance):
        """Знаходить водія й авто за ідентифікаторами і додає поїздку."""
        driver = self._model.find_driver(driver_id)
        vehicle = self._model.find_vehicle(plate)
        trip = Trip(trip_id, driver, vehicle, _parse_datetime(start), _parse_datetime(end),
                    _parse_float(distance, "Відстань"))
        self._model.add_trip(trip)
        logger.info("Додано поїздку %s", trip.trip_id)
        return trip

    def delete_trip(self, trip_id) -> None:
        """Видаляє поїздку (поїздки незмінні: щоб змінити, видаляють і додають заново)."""
        self._model.remove_trip(trip_id)
        logger.info("Видалено поїздку %s", trip_id)

    # ШІ: Claude Code, Claude Opus 5.5 – get_vehicle/get_driver для заповнення форми редагування.
    def get_vehicle(self, plate):
        """Авто за номером (для форми редагування)."""
        return self._model.find_vehicle(plate)

    def get_driver(self, driver_id):
        """Водій за ID (для форми редагування)."""
        return self._model.find_driver(driver_id)

    # ШІ: Claude Code, Claude Opus 5.5 – каркас export_xml_async/_export_worker з пропусками; пропуски заповнив автор.
    def export_xml_async(self, path) -> threading.Thread:
        """Запускає формування XML-звіту про пробіг у фоновому потоці."""
        thread = threading.Thread(target=self._export_worker, args=(path,), daemon=True)
        thread.start()
        return thread

    def _export_worker(self, path) -> None:
        """У фоновому потоці рахує звіт і записує його в XML."""
        try:
            rows = calculate_report(self._model.vehicles, self._model.trips, date.today(),
                                    progress=self._report_progress)
            save_mileage_report(path, rows, date.today())
            logger.info("Експортовано звіт %s: %d авто", path, len(rows))
            self.events.put(("done", f"Звіт збережено: {len(rows)} авто."))
        except (StorageError, ValidationError) as error:
            self.events.put(("error", str(error)))
            logger.warning("Не вдалося експортувати %s: %s", path, error)
        except Exception as error:
            self.events.put(("error", f"Непередбачена помилка: {error}"))
            logger.exception("Непередбачена помилка при експорті %s", path)
