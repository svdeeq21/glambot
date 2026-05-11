import os
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    EVOLUTION_API_URL: str = ""
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "glam-bot"
    ADMIN_WHATSAPP: str = ""  # Owner's number to receive booking alerts
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()


def load_business_config() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "business.yml"
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)
    # Flatten: merge top-level 'business' dict into root for easy access
    flat = {**raw}
    flat.update(raw.get("business", {}))
    return flat


business = load_business_config()
