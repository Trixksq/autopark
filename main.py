# ШІ: Claude Code, Claude Opus 5.5 – точка входу: збирає модель, контролер і вікно, вмикає журнал.
"""Запуск застосунку: python main.py"""
from pathlib import Path

from controllers.fleet_controller import FleetController
from models.fleet import FleetModel
from views.main_window import MainWindow
from services.logging_setup import setup_logging


def main() -> None:
    setup_logging(Path(__file__).parent / "logs" / "fleet.log")
    controller = FleetController(FleetModel())
    MainWindow(controller).mainloop()


if __name__ == "__main__":
    main()
