"""
Centralized configuration for Smart Procurement Platform.
All LLM model assignments are managed here to distribute
Groq API load across multiple models and avoid rate limits.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Smart Procurement Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str

    # Database (for user management only)
    database_url: str

    # Redis (ARQ task queue broker)
    redis_url: str


    # Groq API Key
    groq_api_key: str = ""

    # SerpAPI Key (for online vendor search)
    serp_api_key: str = ""

    # JWT Settings
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Rate Limiting
    rate_limit_per_minute: int = 30

    # CORS settings
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://spend-os.vercel.app"

    @property
    def cors_origins_list(self) -> list[str]:
        """Convert comma-separated string to list of origins and normalize."""
        return [s.strip().rstrip("/") for s in self.allowed_origins.split(",") if s.strip()]

    # Trusted Proxy Hosts for ProxyHeadersMiddleware
    trusted_hosts: str = "127.0.0.1,spend-os-backend.onrender.com"

    @property
    def trusted_hosts_list(self) -> list[str]:
        """Convert comma-separated string to list of trusted hosts."""
        return [s.strip() for s in self.trusted_hosts.split(",") if s.strip()]

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

    @model_validator(mode="after")
    def _validate_required_secrets(self) -> "Settings":
        """Fail fast if critical secrets are missing or empty."""
        errors: list[str] = []

        if not self.secret_key or not self.secret_key.strip():
            errors.append("SECRET_KEY is empty — required for JWT signing")
        if not self.groq_api_key or not self.groq_api_key.strip():
            errors.append("GROQ_API_KEY is missing — required for LLM inference")
        if not self.serp_api_key or not self.serp_api_key.strip():
            errors.append("SERP_API_KEY is missing — required for vendor discovery")

        if errors:
            raise ValueError(
                "\n\n❌ STARTUP ABORTED — invalid configuration:\n  • "
                + "\n  • ".join(errors)
                + "\n\nSet these in your .env file or environment variables.\n"
            )
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
