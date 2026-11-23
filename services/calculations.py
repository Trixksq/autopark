import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class VehicleReport:
    """Підсумок по одному авто."""
    plate: str
    trips_count: int
    distance_km: float
    fuel_l: float
    next_service: date
    days_until_service: int


def split_into_chunks(items, chunk_count: int) -> list:
    """Ділить список на chunk_count частин майже однакового розміру, зберігаючи порядок."""
    if chunk_count < 1:
        raise ValueError("Кількість частин має бути не менше 1.")
    items = list(items)
    if not items:
        return []
    chunk_count = min(chunk_count, len(items))
    size, extra = divmod(len(items), chunk_count)

    chunks = []
    start = 0
    for index in range(chunk_count):
        end = start + size
        if index < extra:
            end += 1
        chunks.append(items[start:end])
        start = end
    return chunks


def summarize_chunk(trips: list) -> dict:
    """Часткові суми для однієї частини поїздок: {номер: [кількість, км, пальне]}"""
    totals = {}
    for trip in trips:
        row = totals.setdefault(trip.vehicle.plate, [0, 0, 0.0])
        row[0] += 1
        row[1] += trip.distance_km
        row[2] += trip.fuel_l
    return totals


def calculate_report(vehicles, trips, today, workers=1, progress=None) -> list:
    """Рахує пальне й терміни ТО. Поїздки діляться на частини й обробляються в workers потоках."""
    if workers < 1:
        raise ValueError("Кількість потоків має бути не менше 1.")
    report = progress or (lambda value: None)
    chunks = split_into_chunks(trips, workers * 4)
    totals = {}
    lock = threading.Lock()
    processed = [0]

    def process(chunk):
        partial = summarize_chunk(chunk)
        with lock:
            for plate, (count, km, fuel) in partial.items():
                row = totals.setdefault(plate, [0, 0, 0.0])
                row[0] += count
                row[1] += km
                row[2] += fuel
            processed[0] += 1
            report(processed[0] / len(chunks))

    if workers == 1:
        for chunk in chunks:
            process(chunk)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(process, chunks))
    report(1.0)
    result = []
    for vehicle in vehicles:
        trips_count, distance_km, fuel_l = totals.get(vehicle.plate, (0, 0, 0.0))
        result.append(VehicleReport(
            plate=vehicle.plate,
            trips_count=trips_count,
            distance_km=distance_km,
            fuel_l=fuel_l,
            next_service=vehicle.next_service_date(),
            days_until_service=vehicle.days_until_service(today),
        ))
    return result
