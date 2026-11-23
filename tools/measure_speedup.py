# ШІ: Claude Code, Claude Opus 5.5 – скрипт вимірювання T1/Tn і прискорення S для calculate_report.
"""Порівнює однопотоковий і багатопотоковий розрахунок пального й термінів ТО.

Запуск з кореня проєкту:
    python tools/measure_speedup.py                              -> data/fleet_big.json
    python tools/measure_speedup.py --file fleet_huge.json --runs 3

Для кожної кількості потоків n розрахунок виконується --runs разів, береться середній час Tn.
Прискорення S = T1 / Tn, ефективність E = S / n.
"""
import argparse
import os
import platform
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.calculations import calculate_report  # noqa: E402
from services.json_storage import load_fleet  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def measure(vehicles, trips, workers: int, runs: int) -> list:
    """Повертає список часів (с) для runs запусків з workers потоками."""
    today = date.today()
    times = []
    for _ in range(runs):
        started = time.perf_counter()
        calculate_report(vehicles, trips, today, workers=workers)
        times.append(time.perf_counter() - started)
    return times


def main() -> None:
    parser = argparse.ArgumentParser(description="Вимірювання прискорення S = T1 / Tn")
    parser.add_argument("--file", default="fleet_big.json", help="файл у папці data")
    parser.add_argument("--runs", type=int, default=5, help="кількість запусків для усереднення")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8], help="кількості потоків")
    args = parser.parse_args()

    vehicles, _, trips = load_fleet(DATA_DIR / args.file)
    gil = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True
    print(f"Набір: {args.file}, поїздок: {len(trips)}, авто: {len(vehicles)}")
    print(f"Python {platform.python_version()}, GIL увімкнено: {gil}, логічних ядер: {os.cpu_count()}")
    print(f"Запусків на кожен режим: {args.runs} (+1 розігрівальний)\n")

    measure(vehicles, trips, 1, 1)
    results = {n: measure(vehicles, trips, n, args.runs) for n in args.workers}
    t1 = statistics.mean(results[1]) if 1 in results else None

    print(f"{'n':>3} | {'Tn сер., с':>10} | {'мін, с':>8} | {'макс, с':>8} | {'S = T1/Tn':>9} | {'E = S/n':>7}")
    print("-" * 60)
    for n, times in results.items():
        tn = statistics.mean(times)
        speedup = t1 / tn if t1 else float("nan")
        print(f"{n:>3} | {tn:>10.3f} | {min(times):>8.3f} | {max(times):>8.3f} | {speedup:>9.2f} | {speedup / n:>7.2f}")


if __name__ == "__main__":
    main()
