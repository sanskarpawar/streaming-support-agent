from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI (direct) — takes priority when set
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_temperature: float = 0.2

    # Azure OpenAI — used as fallback when openai_api_key is empty
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_chat_model: str = "gpt-4.1"
    apim_base_url: str = ""
    apim_subscription_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pagila"

    # Langfuse — env vars: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"  # override with LANGFUSE_BASE_URL

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def use_azure(self) -> bool:
        """True when no direct OpenAI key is configured — fall back to Azure OpenAI."""
        return not bool(self.openai_api_key.strip())

    @property
    def effective_model(self) -> str:
        """The chat model/deployment name to use, depending on the active provider."""
        return self.azure_openai_chat_model if self.use_azure else self.openai_model

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
