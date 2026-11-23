# ШІ: Claude Code, Claude Opus 5.5 – каркас модуля з пропусками (ElementTree); пропуски заповнив автор.
"""XML-звіт про пробіг і пальне (ElementTree)."""
import xml.etree.ElementTree as ET

from models.exceptions import StorageError


def build_mileage_report(rows, generated) -> ET.Element:
    """Будує дерево XML зі списку VehicleReport; generated – дата звіту."""
    root = ET.Element("mileage_report",
                      date=generated.isoformat(),
                      vehicles=str(len(rows)),
                      total_km=f"{sum(r.distance_km for r in rows):.1f}",
                      total_fuel_l=f"{sum(r.fuel_l for r in rows):.2f}")
    for r in rows:
        vehicle = ET.SubElement(root, "vehicle", plate=r.plate,
                                service_due="true" if r.days_until_service <= 0 else "false")
        ET.SubElement(vehicle, "trips").text = str(r.trips_count)
        ET.SubElement(vehicle, "distance_km").text = f"{r.distance_km:.1f}"
        ET.SubElement(vehicle, "fuel_l").text = f"{r.fuel_l:.2f}"                       # 2 знаки після коми
        ET.SubElement(vehicle, "next_service").text = r.next_service.isoformat()
        ET.SubElement(vehicle, "days_until_service").text = str(r.days_until_service)
    return root


def save_mileage_report(path, rows, generated) -> None:
    """Записує звіт у файл UTF-8; помилку файлової системи перетворює на StorageError."""
    tree = ET.ElementTree(build_mileage_report(rows, generated))
    ET.indent(tree)
    try:
        tree.write(path, encoding="utf-8", xml_declaration=True)
    except OSError as error:
        raise StorageError(f"Не вдалося зберегти звіт: {error}") from error

