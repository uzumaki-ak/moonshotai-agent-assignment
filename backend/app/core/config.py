# this file keeps all app settings in one place
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # this class defines typed env vars for the backend
    app_name: str = "moonshot luggage intelligence"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: List[str] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/moonshot_ai"

    llm_chain: str = "gemini,groq,euron,local"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    gemini_model: str = "google/gemini-2.5-flash"
    euron_model: str = "openrouter/auto"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:14b"

    scraper_max_products_per_brand: int = 12
    scraper_max_reviews_per_product: int = 60
    scraper_headless: bool = True
    scraper_timeout_seconds: int = 35
    scraper_delay_ms: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value):
        # this validator supports both csv and json style env values
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # this function caches settings so startup is cheap
    return Settings()
