"""
Centralized configuration for Smart Procurement Platform.
All LLM model assignments are managed here to distribute
Groq API load across multiple models and avoid rate limits.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Smart Procurement Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database (for user management only)
    database_url: str = "postgresql+asyncpg://postgres:root@localhost:5432/smart_procurement"


    # Groq API Key
    groq_api_key: str = ""

    # SerpAPI Key (for online vendor search)
    serp_api_key: str = ""

    # JWT Settings
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Rate Limiting
    rate_limit_per_minute: int = 30

    # CORS settings
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # ─────────────────────────────────────────────────────────────────────────
    # LLM Model Routing (Groq)
    # Each node uses a different model to distribute token usage
    # and avoid per-model rate limits.
    # ─────────────────────────────────────────────────────────────────────────
    llm_vendor_discovery: str = "llama-3.1-8b-instant"
    llm_vendor_enrichment: str = "llama-3.1-8b-instant"
    llm_risk_analysis: str = "llama-3.1-8b-instant"
    llm_reliability_analysis: str = "llama-3.1-8b-instant"
    llm_explanation: str = "llama-3.1-8b-instant"

    # LLM Temperatures
    llm_temperature_discovery: float = 0.1
    llm_temperature_enrichment: float = 0.2
    llm_temperature_risk: float = 0.0
    llm_temperature_reliability: float = 0.0
    llm_temperature_explanation: float = 0.4

    # LLM Max Tokens
    llm_max_tokens: int = 2048

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
