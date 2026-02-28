"""Configuration management using pydantic-settings."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot Configuration
    telegram_bot_token: str = "test_token"

    # LLM Configuration
    llm_provider: str = "openai"  # e.g., "openai", "anthropic", "ollama"
    llm_model: str = "gpt-3.5-turbo"  # e.g., "gpt-4", "claude-3-sonnet", etc.
    llm_api_key: str | None = None  # API key for the LLM provider (if needed)

    # Optional: Default User Configuration
    default_user_telegram_id: str | None = None
    
    # Gamification Configuration
    streak_reduction_rate: float = 2.0
    min_no_reward_probability: float = 10.0
    progress_bar_length: int = 10
    recent_logs_limit: int = 10
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # i18n Configuration
    supported_languages: str | list[str] = ["en", "ru", "kk"]
    default_language: str = "en"

    @model_validator(mode="after")
    def parse_supported_languages(self):
        """Parse comma-separated string to list for supported_languages."""
        if isinstance(self.supported_languages, str):
            # Split comma-separated string and strip whitespace
            self.supported_languages = [
                lang.strip() for lang in self.supported_languages.split(",") if lang.strip()
            ]
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Predefined habit categories with emojis
HABIT_CATEGORIES = [
    ("health", "🏃 Health"),
    ("productivity", "💼 Productivity"),
    ("social", "👥 Social"),
    ("learning", "📚 Learning"),
    ("fitness", "💪 Fitness"),
    ("mindfulness", "🧘 Mindfulness")
]

# Habit validation limits
HABIT_NAME_MAX_LENGTH = 100
HABIT_WEIGHT_MIN = 0
HABIT_WEIGHT_MAX = 30

# Reward validation limits
REWARD_NAME_MAX_LENGTH = 255
REWARD_WEIGHT_MIN = 0.1
REWARD_WEIGHT_MAX = 100
REWARD_PIECES_MIN = 1


# Global settings instance
settings = Settings()
