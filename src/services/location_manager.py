import json
from pathlib import Path


class LocationManager:
    def __init__(self, filepath: str):
        self.regions: dict[int, str] = {}
        self.areas: dict[int, dict[int, str]] = {}
        self.load_data(filepath)

    def load_data(self, filepath: str) -> None:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Файл с локациями не найден: {filepath}")

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        for item in data:
            if item.get("pid") == "1" and "region" in item:
                region_id = int(item["region"])
                self.regions[region_id] = item["labels"]["ru"]
                self.areas.setdefault(region_id, {})

            if item.get("region") == 7 and item.get("type") == "city":
                self.regions[7] = "Минск"
                self.areas.setdefault(7, {})

        for item in data:
            region_id = item.get("region")
            area_id = item.get("area")
            if not region_id or not area_id:
                continue

            region_int = int(region_id)
            area_int = int(area_id)
            area_name = item["labels"]["ru"]
            if region_int in self.areas:
                self.areas[region_int][area_int] = area_name

