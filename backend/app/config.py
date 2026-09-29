from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
PREPARED_ROOT = DATA_ROOT / "prepared"
SIM_ROOT = DATA_ROOT / "sim"
CACHE_ROOT = DATA_ROOT / "cache"

CATEGORIES: tuple[str, ...] = (
    "Home_and_Kitchen",
    "Pet_Supplies",
    "Health_and_Household",
)


class Settings(BaseSettings):
    hindsight_url: str = Field(default="https://api.hindsight.vectorize.io")
    hindsight_api_key: str = Field(default="")
    hindsight_bank: str = Field(default="underdog-lanternfish")
    hindsight_seed_bank: str = Field(default="underdog-seed-w8")

    groq_api_key: str = Field(default="")
    llm_primary: str = Field(default="openai/gpt-oss-120b")
    llm_fallback: str = Field(default="qwen/qwen3-32b")

    sim_seed: int = Field(default=42)

    underdog_db_url: str = Field(default=f"sqlite:///{DATA_ROOT.as_posix()}/underdog.db")
    underdog_shared_secret: str = Field(default="change-me")
    underdog_frontend_origin: str = Field(default="http://localhost:3000")
    demo_mode: bool = Field(default=True)

    keepa_api_key: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
