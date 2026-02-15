import json
from pathlib import Path
import logging

from src.app_context import AppContext


class TargetStorage:
    def __init__(self, filepath: str):
        self.path = Path(filepath)

    def load(self, context: AppContext) -> None:
        if not self.path.exists():
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as error:
            logging.warning("Не удалось прочитать %s: %s", self.path, error)
            return

        targets = raw.get("targets", [])
        for target in targets:
            try:
                category_id = int(target.get("category_id", 0))
                if category_id <= 0:
                    continue
                created = context.add_target(
                    name=target.get("name", f"Категория {category_id}"),
                    category_id=category_id,
                    extra_params=target.get("extra_params") or {},
                )
                created.enabled = bool(target.get("enabled", True))
            except Exception as error:
                logging.warning("Пропущена битая запись target в %s: %s", self.path, error)

    def save(self, context: AppContext) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "targets": [
                {
                    "name": target.name,
                    "category_id": target.category_id,
                    "extra_params": target.extra_params,
                    "enabled": target.enabled,
                }
                for target in context.targets.values()
            ]
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
