from dataclasses import dataclass, field
from typing import Any

from src.models.search_config import SearchConfig
from src.services.kufar_parser import KufarParser
from src.services.location_manager import LocationManager


@dataclass
class AppContext:
    location_manager: LocationManager
    parser: KufarParser
    search_config: SearchConfig = field(default_factory=SearchConfig)
    browsing_sessions: dict[int, dict[str, Any]] = field(default_factory=dict)
    seen_ads: set[int] = field(default_factory=set)
    ad_photos_cache: dict[Any, list[str]] = field(default_factory=dict)

