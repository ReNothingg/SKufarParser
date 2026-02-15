from dataclasses import dataclass
import os

from dotenv import load_dotenv


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

@dataclass(frozen=True)
class AppConfig:
    bot_token: str
    user_id: int
    check_interval: int
    locations_file: str
    targets_file: str
    kufar_auth_token: str | None
    user_agent: str

    @property
    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        if self.kufar_auth_token:
            headers["Authorization"] = self.kufar_auth_token
        return headers


def load_config() -> AppConfig:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("Переменная BOT_TOKEN обязательна.")

    user_id_raw = os.getenv("USER_ID", "").strip()
    if not user_id_raw:
        raise ValueError("Переменная USER_ID обязательна.")
    try:
        user_id = int(user_id_raw)
    except ValueError as error:
        raise ValueError("USER_ID должен быть числом.") from error

    check_interval_raw = os.getenv("CHECK_INTERVAL", "60").strip()
    try:
        check_interval = int(check_interval_raw)
    except ValueError as error:
        raise ValueError("CHECK_INTERVAL должен быть числом.") from error

    locations_file = os.getenv("LOCATIONS_FILE", "data/locations.json").strip() or "data/locations.json"
    targets_file = os.getenv("TARGETS_FILE", "data/targets.json").strip() or "data/targets.json"
    kufar_auth_token = os.getenv("KUFAR_AUTH_TOKEN", "").strip() or None
    user_agent = os.getenv("KUFAR_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT

    return AppConfig(
        bot_token=bot_token,
        user_id=user_id,
        check_interval=check_interval,
        locations_file=locations_file,
        targets_file=targets_file,
        kufar_auth_token=kufar_auth_token,
        user_agent=user_agent,
    )
