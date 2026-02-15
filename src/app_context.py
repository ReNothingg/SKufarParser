from dataclasses import dataclass, field
from typing import Any

from src.models.search_config import SearchConfig
from src.models.search_target import SearchTarget
from src.services.kufar_parser import KufarParser
from src.services.location_manager import LocationManager


@dataclass
class AppContext:
    location_manager: LocationManager
    parser: KufarParser
    search_config: SearchConfig = field(default_factory=SearchConfig)
    browsing_sessions: dict[int, dict[str, Any]] = field(default_factory=dict)
    targets: dict[int, SearchTarget] = field(default_factory=dict)
    seen_ads_by_target: dict[int, set[int]] = field(default_factory=dict)
    ad_photos_cache: dict[Any, list[str]] = field(default_factory=dict)
    _next_target_id: int = 1

    def add_target(self, name: str, category_id: int, extra_params: dict[str, str] | None = None) -> SearchTarget:
        target = SearchTarget(
            target_id=self._next_target_id,
            name=name,
            category_id=category_id,
            extra_params=extra_params or {},
        )
        self.targets[target.target_id] = target
        self.seen_ads_by_target[target.target_id] = set()
        self._next_target_id += 1
        return target

    def remove_target(self, target_id: int) -> bool:
        if target_id not in self.targets:
            return False
        self.targets.pop(target_id, None)
        self.seen_ads_by_target.pop(target_id, None)
        return True

    def toggle_target(self, target_id: int) -> SearchTarget | None:
        target = self.targets.get(target_id)
        if not target:
            return None
        target.enabled = not target.enabled
        return target

    def get_active_targets(self) -> list[SearchTarget]:
        return [target for target in self.targets.values() if target.enabled]
