# ШІ: Claude Code, Claude Opus 5.5 – чернетка таблиці ttk.Treeview з прокруткою і сортуванням кліком по заголовку.
"""Таблиця для всіх вкладок головного вікна."""
from dataclasses import dataclass
from tkinter import ttk

import customtkinter as ctk


@dataclass(frozen=True)
class TableRow:
    """Рядок таблиці: що показати, за чим сортувати, підсвічування і ідентифікатор запису."""
    values: tuple
    sort_keys: tuple
    tags: tuple = ()
    row_id: str = ""


class TableFrame(ctk.CTkFrame):
    """Treeview з вертикальною прокруткою; клік по заголовку сортує за стовпцем, повторний – у зворотному порядку."""

    def __init__(self, master, columns: tuple):
        super().__init__(master)
        self._columns = columns
        self._rows = []
        self._sort_index = None
        self._reverse = False
        self._tree = ttk.Treeview(self, columns=[key for key, _, _ in columns], show="headings",
                                  selectmode="browse")
        for index, (key, title, width) in enumerate(columns):
            self._tree.heading(key, text=title, command=lambda i=index: self._on_heading(i))
            self._tree.column(key, width=width, anchor="center")
        self._tree.tag_configure("due", foreground="#c62828")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def show(self, rows: list) -> None:
        """Замінює вміст таблиці; поточне сортування зберігається."""
        self._rows = list(rows)
        self._redraw()

    def selected_id(self) -> str | None:
        """row_id виділеного рядка або None, якщо нічого не виділено."""
        selection = self._tree.selection()
        return selection[0] if selection else None

    def _on_heading(self, index: int) -> None:
        self._reverse = not self._reverse if self._sort_index == index else False
        self._sort_index = index
        self._redraw()

    def _redraw(self) -> None:
        rows = self._rows
        if self._sort_index is not None:
            rows = sorted(rows, key=lambda row: row.sort_keys[self._sort_index], reverse=self._reverse)
        self._tree.delete(*self._tree.get_children())
        for number, row in enumerate(rows):
            self._tree.insert("", "end", iid=row.row_id or str(number), values=row.values, tags=row.tags)
        for index, (key, title, _) in enumerate(self._columns):
            arrow = (" ▼" if self._reverse else " ▲") if index == self._sort_index else ""
            self._tree.heading(key, text=title + arrow)
