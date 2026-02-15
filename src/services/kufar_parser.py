import json
import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from src.models.search_config import SearchConfig


PLACEHOLDER_IMAGE = "https://via.placeholder.com/800x600.png?text=Нет+фото"
BASE_SEARCH_URL = (
    "https://api.kufar.by/search-api/v2/search/rendered-paginated"
    "?cat=17010&lang=ru&pb=5&prn=17000&size=50&sort=lst.d"
)


class KufarParser:
    def __init__(self, headers: dict[str, str]):
        self._session: aiohttp.ClientSession | None = None
        self._headers = headers

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def build_url(self, config: SearchConfig) -> str:
        url = BASE_SEARCH_URL
        if config.rgn:
            url += f"&rgn={config.rgn}"
        if config.ar:
            url += f"&ar={config.ar}"
        return url

    async def fetch_search_results(self, config: SearchConfig) -> list[dict[str, Any]]:
        session = await self._get_session()
        url = self.build_url(config)
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                return data.get("ads", [])
        except Exception as error:
            logging.error("Ошибка поиска: %s", error)
            return []

    async def fetch_ad_details(self, ad_link: str) -> dict[str, Any] | None:
        session = await self._get_session()
        try:
            async with session.get(ad_link) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")
                script = soup.find("script", id="__NEXT_DATA__")
                if not script or not script.string:
                    return None

                parsed = json.loads(script.string)
                return parsed["props"]["initialState"]["adView"]["data"]
        except Exception:
            return None

    @staticmethod
    def _parse_numeric_price(price_value: Any) -> float:
        try:
            if not price_value:
                return 0
            return int(price_value) / 100
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def get_all_photos(ad_data: dict[str, Any]) -> list[str]:
        images: list[str] = []
        image_data = ad_data.get("images", {})

        if isinstance(image_data, dict):
            gallery = image_data.get("gallery", [])
            if isinstance(gallery, list):
                images = gallery
            elif isinstance(gallery, dict):
                images = gallery.get("images", [])

            if not images:
                images = image_data.get("listings", [])

        if not images and isinstance(image_data, list):
            for image in image_data:
                if isinstance(image, dict) and "path" in image:
                    images.append(f"https://rms.kufar.by/v1/gallery/{image['path']}")
                elif isinstance(image, str):
                    images.append(image)

        valid_images = [img for img in images if isinstance(img, str) and img.startswith("http")]
        return valid_images if valid_images else [PLACEHOLDER_IMAGE]

    def format_caption(
        self,
        ad_data: dict[str, Any],
        current_index: int | None = None,
        total_count: int | None = None,
    ) -> str:
        subject = ad_data.get("subject", "Без названия")

        price_str = ad_data.get("price")
        if not price_str:
            price_byn = self._parse_numeric_price(ad_data.get("price_byn"))
            if price_byn > 0:
                price_str = f"{price_byn:,.0f} р.".replace(",", " ")
            else:
                price_str = "Договорная"

        price_usd = self._parse_numeric_price(ad_data.get("price_usd") or ad_data.get("priceUsd"))
        if price_usd > 0:
            price_str += f" (~${price_usd:,.0f})"

        params: list[str] = []
        source_params = ad_data.get("adParams") or ad_data.get("ad_parameters")
        if source_params:
            iterator = source_params.values() if isinstance(source_params, dict) else source_params
            for param in iterator:
                if not isinstance(param, dict):
                    continue
                if param.get("p") in {"category", "type", "area", "region", "images"}:
                    continue
                value = param.get("vl", "")
                if isinstance(value, list):
                    value = ", ".join(map(str, value))
                params.append(f"▫️ {param.get('pl')}: {value}")

        description = ad_data.get("description") or ad_data.get("body") or ""
        description = description.replace("<br>", "\n").replace("&nbsp;", " ").strip()
        if len(description) > 600:
            description = f"{description[:600]}..."

        header = ""
        if current_index is not None and total_count is not None:
            header = f"🗂 <b>{current_index + 1} из {total_count}</b>\n"

        params_text = "\n".join(params[:5])
        return (
            f"{header}📱 <b>{subject}</b>\n"
            f"💰 <b>{price_str}</b>\n\n"
            f"{params_text}\n\n"
            f"📝 <i>{description}</i>\n\n"
            f"📍 {ad_data.get('region', 'Беларусь')}\n"
        )

