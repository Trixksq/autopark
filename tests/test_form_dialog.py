# ШІ: Claude Code, Claude Opus 5.5 – тести діалогового вікна форми FormDialog.
"""Перевірка FormDialog без контролера: форма лише збирає рядки і показує помилки.
Запуск: python -m unittest tests.test_form_dialog (потрібен customtkinter, тобто інтерпретатор з .venv)."""
import gc
import unittest

import customtkinter as ctk

from models.exceptions import NotFoundError, ValidationError
from views.form_dialog import FormDialog

FIELDS = (
    ("type", "Тип", ("Легковий", "Вантажний", "Автобус")),
    ("plate", "Номер"),
    ("brand", "Марка"),
)
INITIAL = {"type": "Вантажний", "plate": "ВН1234АА", "brand": "MAN"}


class FormDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # одне головне вікно на всі тести: CustomTkinter не любить, коли CTk() створюють і знищують багато разів
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.quit()
        cls.root.destroy()
        cls.root = None
        # Прибираємо «сміття» Tk (шрифти, змінні) тут, у головному потоці. Інакше збирач сміття може
        # запустити їхні __del__ у фоновому потоці наступних тестів, а Tk дозволяє виклики лише з головного.
        gc.collect()

    def setUp(self):
        self.received = []
        self.dialog = None

    def tearDown(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.pump(50)

    def pump(self, ms: int = 300) -> None:
        """Дає вікну попрацювати ms мілісекунд: CustomTkinter і форма виконують відкладені через after() дії."""
        self.root.after(ms, self.root.quit)
        self.root.mainloop()

    def make(self, on_submit=None, **kwargs):
        self.dialog = FormDialog(self.root, "Тест", FIELDS, on_submit or self.received.append, **kwargs)
        self.pump()
        return self.dialog

    def test_initial_values_are_shown(self):
        dialog = self.make(initial=INITIAL)
        self.assertEqual(dialog.values(), INITIAL)

    def test_empty_form(self):
        dialog = self.make()
        values = dialog.values()
        self.assertEqual(set(values), {"type", "plate", "brand"})
        self.assertEqual(values["plate"], "")
        self.assertEqual(values["type"], "Легковий")

    def test_submit_passes_values_and_closes(self):
        dialog = self.make(initial=INITIAL)
        dialog.submit()
        self.assertEqual(self.received, [INITIAL])
        self.assertFalse(dialog.winfo_exists())

    def test_validation_error_keeps_form_open(self):
        def reject(values):
            raise ValidationError("Номер має формат ВН1234АА.")

        dialog = self.make(reject, initial=INITIAL)
        dialog.submit()
        self.assertTrue(dialog.winfo_exists())
        self.assertIn("ВН1234АА", dialog.error_text)
        self.assertEqual(dialog.values(), INITIAL)

    def test_subclass_errors_are_shown_too(self):
        def reject(values):
            raise NotFoundError("Водія D99 не знайдено.")

        dialog = self.make(reject)
        dialog.submit()
        self.assertTrue(dialog.winfo_exists())
        self.assertIn("D99", dialog.error_text)

    def test_cancel_closes_without_submit(self):
        dialog = self.make(initial=INITIAL)
        dialog.cancel()
        self.assertEqual(self.received, [])
        self.assertFalse(dialog.winfo_exists())

    def test_locked_field_keeps_value(self):
        dialog = self.make(initial=INITIAL, locked=("plate",))
        self.assertEqual(dialog.values()["plate"], "ВН1234АА")
        dialog.submit()
        self.assertEqual(self.received[0]["plate"], "ВН1234АА")


if __name__ == "__main__":
    unittest.main()
