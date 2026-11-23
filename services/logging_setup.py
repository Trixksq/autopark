# ШІ: Claude Code, Claude Opus 5.5 – каркас setup_logging з пропусками; пропуски заповнив автор.
"""Налаштування журналу застосунку."""
import logging
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"


def setup_logging(path) -> logging.Handler:
    """Пише журнал у файл path (UTF-8); повертає обробник, щоб його можна було закрити."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler
