from dataclasses import dataclass, field


@dataclass
class SearchTarget:
    target_id: int
    name: str
    category_id: int
    extra_params: dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    @property
    def short_label(self) -> str:
        status = "🟢" if self.enabled else "⏸"
        return f"{status} {self.name}"

    @property
    def debug_label(self) -> str:
        parts = [f"cat={self.category_id}"]
        for key in sorted(self.extra_params):
            parts.append(f"{key}={self.extra_params[key]}")
        return "&".join(parts)

