# ШІ: Claude Code, Claude Opus 5.5 – розмітка головного вікна: вкладки «Транспорт», «Водії», «Поїздки»,
# «Розрахунки»; пошук і фільтр за типом; відкриття і збереження JSON у фоні, прогрес-бар,
# опитування черги подій через after(); кнопки «Додати/Змінити/Видалити» на вкладках і їхні обробники.
"""Головне вікно застосунку обліку автопарку."""
import queue
import time
import customtkinter as ctk

from datetime import date
from tkinter import filedialog, messagebox

from views.table_frame import TableFrame, TableRow
from views.form_dialog import FormDialog
from models.exceptions import ValidationError

POLL_MS = 100
MAX_TRIP_ROWS = 2000
DATE_FORMAT = "%d.%m.%Y"
DATETIME_FORMAT = "%d.%m.%Y %H:%M"
ALL_TYPES = "Усі типи"
TYPE_NAMES = {"Car": "Легковий", "Truck": "Вантажний", "Bus": "Автобус"}
WORKER_CHOICES = ("1", "2", "4", "8")

VEHICLE_COLUMNS = (
    ("type", "Тип", 100), ("plate", "Номер", 100), ("brand", "Марка", 120), ("year", "Рік", 60),
    ("mileage", "Пробіг, км", 100), ("last_service", "Останнє ТО", 100),
    ("next_service", "Наступне ТО", 100), ("days_left", "Днів до ТО", 90),
)
DRIVER_COLUMNS = (("id", "ID", 80), ("name", "ПІБ", 320), ("categories", "Категорії", 160))
TRIP_COLUMNS = (
    ("id", "ID", 80), ("driver", "Водій", 80), ("plate", "Авто", 100), ("start", "Початок", 140),
    ("end", "Кінець", 140), ("km", "Км", 70), ("fuel", "Пальне, л", 90),
)
REPORT_COLUMNS = (
    ("plate", "Номер", 100), ("trips", "Поїздок", 80), ("km", "Км", 100), ("fuel", "Пальне, л", 110),
    ("next_service", "Наступне ТО", 110), ("days_left", "Днів до ТО", 100),
)

# Поля форм: (ключ, підпис) або (ключ, підпис, варіанти вибору)
VEHICLE_FIELDS = (
    ("type", "Тип", tuple(TYPE_NAMES.values())),
    ("plate", "Номер (ВН1234АА)"),
    ("brand", "Марка"),
    ("year", "Рік випуску"),
    ("mileage", "Пробіг, км"),
    ("last_service", "Останнє ТО (ДД.ММ.РРРР)"),
)
DRIVER_FIELDS = (("id", "ID"), ("name", "ПІБ"), ("categories", "Категорії (B, C)"))
TRIP_FIELDS = (
    ("id", "ID"), ("driver", "ID водія"), ("plate", "Номер авто"),
    ("start", "Початок (ДД.ММ.РРРР ГГ:ХХ)"), ("end", "Кінець (ДД.ММ.РРРР ГГ:ХХ)"), ("km", "Відстань, км"),
)
TYPE_KEYS = {name: key for key, name in TYPE_NAMES.items()}  # «Легковий» → «Car»


def type_name(vehicle) -> str:
    """Українська назва типу транспорту за назвою класу."""
    return TYPE_NAMES.get(type(vehicle).__name__, type(vehicle).__name__)


class MainWindow(ctk.CTk):
    """Представлення (View): показує дані й передає дії користувача контролеру."""

    def __init__(self, controller):
        super().__init__()
        self._controller = controller
        self._report_rows = []
        self._task_started = 0.0
        self.title("Облік автопарку")
        self.geometry("1000x620")
        self._build_toolbar()
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._build_vehicles_tab(tabs.add("Транспорт"))
        self._build_drivers_tab(tabs.add("Водії"))
        self._build_trips_tab(tabs.add("Поїздки"))
        self._build_report_tab(tabs.add("Розрахунки"))
        self.refresh_all()

    # ---------- розмітка ----------

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=10, pady=(10, 5))
        self._open_button = ctk.CTkButton(bar, text="Відкрити JSON…", command=self._on_open)
        self._open_button.pack(side="left", padx=5, pady=5)
        self._save_button = ctk.CTkButton(bar, text="Зберегти JSON…", command=self._on_save)
        self._save_button.pack(side="left", padx=5, pady=5)
        self._export_button = ctk.CTkButton(bar, text="Звіт XML…", command=self._on_export)
        self._export_button.pack(side="left", padx=5, pady=5)
        self._progress = ctk.CTkProgressBar(bar)
        self._progress.set(0)
        self._progress.pack(side="left", fill="x", expand=True, padx=10)
        self._message = ctk.CTkLabel(bar, text="Відкрийте файл з даними", width=380, anchor="w")
        self._message.pack(side="right", padx=5)

    def _build_vehicles_tab(self, tab) -> None:
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 5))
        self._search = ctk.CTkEntry(bar, placeholder_text="Пошук за номером", width=220)
        self._search.pack(side="left", padx=5)
        self._search.bind("<KeyRelease>", lambda _event: self.refresh_vehicles())
        self._type_filter = ctk.CTkOptionMenu(bar, values=[ALL_TYPES, *TYPE_NAMES.values()],
                                              command=lambda _value: self.refresh_vehicles())
        self._type_filter.pack(side="left", padx=5)
        self._add_crud_buttons(bar, self._add_vehicle, self._edit_vehicle, self._delete_vehicle)
        self._vehicles_status = ctk.CTkLabel(bar, text="")
        self._vehicles_status.pack(side="right", padx=10)
        self._vehicles_table = TableFrame(tab, VEHICLE_COLUMNS)
        self._vehicles_table.pack(fill="both", expand=True)

    def _build_drivers_tab(self, tab) -> None:
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 5))
        self._add_crud_buttons(bar, self._add_driver, self._edit_driver, self._delete_driver)
        self._drivers_table = TableFrame(tab, DRIVER_COLUMNS)
        self._drivers_table.pack(fill="both", expand=True)

    def _build_trips_tab(self, tab) -> None:
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 5))
        self._add_crud_buttons(bar, self._add_trip, None, self._delete_trip)  # поїздка незмінна: без «Змінити»
        self._trips_status = ctk.CTkLabel(bar, text="", anchor="w")
        self._trips_status.pack(side="right", padx=10)
        self._trips_table = TableFrame(tab, TRIP_COLUMNS)
        self._trips_table.pack(fill="both", expand=True)

    def _add_crud_buttons(self, bar, on_add, on_edit, on_delete) -> None:
        """Кнопки «Додати», «Змінити», «Видалити»; кнопку з command=None не створюємо."""
        for text, command in (("Додати", on_add), ("Змінити", on_edit), ("Видалити", on_delete)):
            if command is not None:
                ctk.CTkButton(bar, text=text, width=90, command=command).pack(side="left", padx=3)

    def _build_report_tab(self, tab) -> None:
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(bar, text="Потоків:").pack(side="left", padx=5)
        self._workers = ctk.CTkSegmentedButton(bar, values=list(WORKER_CHOICES))
        self._workers.set(WORKER_CHOICES[2])
        self._workers.pack(side="left", padx=5)
        self._report_button = ctk.CTkButton(bar, text="Розрахувати пальне і ТО", command=self._on_calculate)
        self._report_button.pack(side="left", padx=10)
        self._report_status = ctk.CTkLabel(bar, text="")
        self._report_status.pack(side="right", padx=10)
        self._report_table = TableFrame(tab, REPORT_COLUMNS)
        self._report_table.pack(fill="both", expand=True)

    # ---------- заповнення таблиць ----------

    def refresh_all(self) -> None:
        self.refresh_vehicles()
        self._drivers_table.show([self._driver_row(d) for d in self._controller.list_drivers()])
        trips = self._controller.list_trips()
        shown = trips[:MAX_TRIP_ROWS]
        self._trips_table.show([self._trip_row(t) for t in shown])
        self._trips_status.configure(text=f"Поїздок: {len(trips)}" +
                                          (f" (показано перші {len(shown)})" if len(shown) < len(trips) else ""))

    def refresh_vehicles(self) -> None:
        """Перемальовує таблицю транспорту за пошуком і фільтром типу."""
        today = date.today()
        wanted = self._type_filter.get()
        vehicles = [v for v in self._controller.search_vehicles(self._search.get())
                    if wanted == ALL_TYPES or type_name(v) == wanted]
        self._vehicles_table.show([self._vehicle_row(v, today) for v in vehicles])
        self._vehicles_status.configure(text=f"Показано: {len(vehicles)}")

    @staticmethod
    def _vehicle_row(vehicle, today: date) -> TableRow:
        days_left = vehicle.days_until_service(today)
        return TableRow(
            values=(type_name(vehicle), vehicle.plate, vehicle.brand, vehicle.year,
                    f"{vehicle.mileage:,}".replace(",", " "), vehicle.last_service.strftime(DATE_FORMAT),
                    vehicle.next_service_date().strftime(DATE_FORMAT), days_left),
            sort_keys=(type_name(vehicle), vehicle.plate, vehicle.brand, vehicle.year, vehicle.mileage,
                       vehicle.last_service, vehicle.next_service_date(), days_left),
            tags=("due",) if vehicle.is_service_due(today) else (),
            row_id=vehicle.plate,
        )

    @staticmethod
    def _driver_row(driver) -> TableRow:
        categories = ", ".join(sorted(driver.categories))
        return TableRow(values=(driver.driver_id, driver.full_name, categories),
                        sort_keys=(driver.driver_id, driver.full_name, categories), row_id=driver.driver_id)

    @staticmethod
    def _trip_row(trip) -> TableRow:
        return TableRow(
            values=(trip.trip_id, trip.driver.driver_id, trip.vehicle.plate, trip.start.strftime(DATETIME_FORMAT),
                    trip.end.strftime(DATETIME_FORMAT), trip.distance_km, f"{trip.fuel_l:.1f}"),
            sort_keys=(trip.trip_id, trip.driver.driver_id, trip.vehicle.plate, trip.start, trip.end,
                       trip.distance_km, trip.fuel_l),
            row_id=trip.trip_id,
        )

    def _show_report(self) -> None:
        rows = [TableRow(
            values=(r.plate, r.trips_count, f"{r.distance_km:,}".replace(",", " "),
                    f"{r.fuel_l:,.1f}".replace(",", " "),
                    r.next_service.strftime(DATE_FORMAT), r.days_until_service),
            sort_keys=(r.plate, r.trips_count, r.distance_km, r.fuel_l, r.next_service, r.days_until_service),
            tags=("due",) if r.days_until_service <= 0 else (),
            row_id=r.plate,
        ) for r in self._report_rows]
        self._report_table.show(rows)

    # ---------- CRUD: форми додавання, редагування, видалення ----------

    def _selected(self, table: TableFrame, action: str) -> str | None:
        """row_id виділеного рядка; якщо нічого не виділено – підказка користувачу і None."""
        row_id = table.selected_id()
        if row_id is None:
            messagebox.showinfo(action, "Спершу виберіть рядок у таблиці.")
        return row_id

    def _confirm_delete(self, question: str, delete) -> None:
        """Питає підтвердження і видаляє; помилку моделі (наприклад, «Водій має поїздки») показує у вікні."""
        if not messagebox.askyesno("Видалити", question):
            return
        try:
            delete()
        except ValidationError as error:
            messagebox.showerror("Помилка", str(error))
            return
        self.refresh_all()

    def _add_vehicle(self) -> None:
        def save(v: dict) -> None:
            self._controller.add_vehicle(TYPE_KEYS[v["type"]], v["plate"], v["brand"],
                                         v["year"], v["mileage"], v["last_service"])
            self.refresh_all()

        FormDialog(self, "Нове авто", VEHICLE_FIELDS, save)

    def _edit_vehicle(self) -> None:
        plate = self._selected(self._vehicles_table, "Змінити")
        if plate is None:
            return
        vehicle = self._controller.get_vehicle(plate)
        initial = {"type": type_name(vehicle), "plate": vehicle.plate, "brand": vehicle.brand,
                   "year": str(vehicle.year), "mileage": str(vehicle.mileage),
                   "last_service": vehicle.last_service.strftime(DATE_FORMAT)}

        def save(v: dict) -> None:
            self._controller.update_vehicle(plate, v["brand"], v["year"], v["mileage"], v["last_service"])
            self.refresh_all()

        FormDialog(self, f"Авто {plate}", VEHICLE_FIELDS, save, initial=initial, locked=("type", "plate"))

    def _delete_vehicle(self) -> None:
        plate = self._selected(self._vehicles_table, "Видалити")
        if plate is not None:
            self._confirm_delete(f"Видалити авто {plate}?", lambda: self._controller.delete_vehicle(plate))

    def _add_driver(self) -> None:
        def save(v: dict) -> None:
            self._controller.add_driver(v["id"], v["name"], v["categories"])
            self.refresh_all()

        FormDialog(self, "Новий водій", DRIVER_FIELDS, save)

    def _edit_driver(self) -> None:
        driver_id = self._selected(self._drivers_table, "Змінити")
        if driver_id is None:
            return
        driver = self._controller.get_driver(driver_id)
        initial = {"id": driver.driver_id, "name": driver.full_name,
                   "categories": ", ".join(sorted(driver.categories))}

        def save(v: dict) -> None:
            self._controller.update_driver(driver_id, v["name"], v["categories"])
            self.refresh_all()

        FormDialog(self, f"Водій {driver_id}", DRIVER_FIELDS, save, initial=initial, locked=("id",))

    def _delete_driver(self) -> None:
        driver_id = self._selected(self._drivers_table, "Видалити")
        if driver_id is not None:
            self._confirm_delete(f"Видалити водія {driver_id}?", lambda: self._controller.delete_driver(driver_id))

    def _add_trip(self) -> None:
        def save(v: dict) -> None:
            self._controller.add_trip(v["id"], v["driver"], v["plate"], v["start"], v["end"], v["km"])
            self.refresh_all()

        FormDialog(self, "Нова поїздка", TRIP_FIELDS, save)

    def _delete_trip(self) -> None:
        trip_id = self._selected(self._trips_table, "Видалити")
        if trip_id is not None:
            self._confirm_delete(f"Видалити поїздку {trip_id}?", lambda: self._controller.delete_trip(trip_id))

    # ---------- фонові задачі ----------

    def _on_open(self) -> None:
        path = filedialog.askopenfilename(title="Відкрити набір", filetypes=[("JSON", "*.json")])
        if path:
            self._start_task(lambda: self._controller.open_file_async(path), "Завантаження…")

    def _on_save(self) -> None:
        path = filedialog.asksaveasfilename(title="Зберегти набір", defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            self._start_task(lambda: self._controller.save_file_async(path), "Збереження…")

    def _on_export(self) -> None:
        path = filedialog.asksaveasfilename(title="Зберегти звіт", defaultextension=".xml",
                                            filetypes=[("XML", "*.xml")])
        if path:
            self._start_task(lambda: self._controller.export_xml_async(path), "Формування звіту…")

    def _on_calculate(self) -> None:
        workers = int(self._workers.get())
        self._start_task(lambda: self._controller.calculate_async(workers), f"Розрахунок у {workers} потоках…")

    def _start_task(self, action, message: str) -> None:
        """Блокує кнопки, запускає фонову задачу контролера і починає опитувати чергу."""
        self._set_buttons_state("disabled")
        self._progress.set(0)
        self._message.configure(text=message)
        self._task_started = time.perf_counter()
        action()
        self.after(POLL_MS, self._poll_events)

    def _poll_events(self) -> None:
        """Головний потік: забирає з черги всі події фонової задачі й оновлює віджети."""
        while True:
            try:
                kind, payload = self._controller.events.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                self._progress.set(payload)
            elif kind == "report":
                self._report_rows = payload
            elif kind == "done":
                self._finish_task(payload)
                return
            elif kind == "error":
                self._finish_task("Помилка")
                messagebox.showerror("Помилка", payload)
                return
        self.after(POLL_MS, self._poll_events)

    def _finish_task(self, message: str) -> None:
        elapsed = time.perf_counter() - self._task_started
        self._set_buttons_state("normal")
        self._message.configure(text=message)
        self._report_status.configure(text=f"Остання задача: {elapsed:.2f} с")
        self._show_report()
        self.refresh_all()

    def _set_buttons_state(self, state: str) -> None:
        for button in (self._open_button, self._save_button, self._report_button, self._export_button):
            button.configure(state=state)
