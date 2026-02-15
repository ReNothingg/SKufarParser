from dataclasses import dataclass


@dataclass
class SearchConfig:
    rgn: int | None = None
    ar: int | None = None
    rgn_name: str = "Вся Беларусь"
    ar_name: str = ""

    def set_countrywide(self) -> None:
        self.rgn = None
        self.ar = None
        self.rgn_name = "Вся Беларусь"
        self.ar_name = ""

    def set_region(self, region_id: int, region_name: str) -> None:
        self.rgn = region_id
        self.rgn_name = region_name

    def set_area(self, area_id: int | None, area_name: str = "") -> None:
        self.ar = area_id
        self.ar_name = area_name

    @property
    def location_label(self) -> str:
        return f"{self.rgn_name}{self.ar_name}"

