# ШІ: Claude Code, Claude Opus 5.5 – каркас класу FormDialog з пропусками; пропуски заповнив автор.
import customtkinter as ctk

from models.exceptions import ValidationError


class FormDialog(ctk.CTkToplevel):
    """Вікно з полями; кнопка «Зберегти» передає рядки в on_submit, помилки показує у вікні."""

    def __init__(self, master, title, fields, on_submit, initial=None, locked=()):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self._on_submit = on_submit
        self._widgets = {}
        initial = initial or {}
        for row, field in enumerate(fields):
            key, label = field[0], field[1]
            ctk.CTkLabel(self, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=10, pady=4)
            if len(field) > 2:
                widget = ctk.CTkOptionMenu(self, values=list(field[2]))
                if key in initial:
                    widget.set(initial[key])
            else:
                widget = ctk.CTkEntry(self, width=240)
                widget.insert(0, initial.get(key, ""))
            if key in locked:
                widget.configure(state="disabled")
            widget.grid(row=row, column=1, padx=10, pady=4)
            self._widgets[key] = widget
        self._error = ctk.CTkLabel(self, text="", text_color="#c62828", wraplength=360)
        self._error.grid(row=len(fields), column=0, columnspan=2, padx=10)
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)
        ctk.CTkButton(buttons, text="Зберегти", command=self.submit).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text="Скасувати", command=self.cancel).pack(side="left", padx=5)
        self.transient(master)
        self.after(50, self._make_modal)

    def _make_modal(self) -> None:
        """Забороняє клацати по головному вікну, поки відкрита форма."""
        if self.winfo_exists():
            self.grab_set()

    def values(self) -> dict:
        return {key: widget.get() for key, widget in self._widgets.items()}

    @property
    def error_text(self) -> str:
        return self._error.cget("text")

    def submit(self) -> None:
        try:
            self._on_submit(self.values())
        except ValidationError as error:
            self._error.configure(text=str(error))
            return
        self.destroy()

    def cancel(self) -> None:
        self.destroy()
