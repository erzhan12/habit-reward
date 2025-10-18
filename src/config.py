"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Airtable Configuration
    airtable_api_key: str = "test_key"
    airtable_base_id: str = "test_base"

    # Telegram Bot Configuration
    telegram_bot_token: str = "test_token"

    # LLM Configuration
    llm_provider: str = "openai"  # e.g., "openai", "anthropic", "ollama"
    llm_model: str = "gpt-3.5-turbo"  # e.g., "gpt-4", "claude-3-sonnet", etc.
    llm_api_key: str | None = None  # API key for the LLM provider (if needed)

    # Optional: Default User Configuration
    default_user_telegram_id: str | None = None
    
    # Gamification Configuration
    streak_multiplier_rate: float = 0.1
    progress_bar_length: int = 10
    recent_logs_limit: int = 10
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
