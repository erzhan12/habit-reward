"""API-specific configuration settings."""

import logging
import secrets
import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Generate a fallback key for development only
_DEV_SECRET_KEY = secrets.token_urlsafe(32)


class APISettings(BaseSettings):
    """API configuration loaded from environment variables."""

    # JWT Configuration
    # IMPORTANT: Set API_SECRET_KEY in production to persist across restarts
    api_secret_key: str = ""
    api_access_token_expire_minutes: int = 15
    api_refresh_token_expire_days: int = 7
    api_algorithm: str = "HS256"

    def get_secret_key(self) -> str:
        """Get the JWT secret key, with warning if using fallback.

        Returns:
            The configured secret key, or a development fallback with warning.
        """
        if self.api_secret_key:
            return self.api_secret_key

        warnings.warn(
            "API_SECRET_KEY not set! Using ephemeral key that changes on restart. "
            "Set API_SECRET_KEY environment variable for production.",
            RuntimeWarning,
            stacklevel=2
        )
        logger.warning(
            "API_SECRET_KEY not configured. JWT tokens will be invalidated on restart. "
            "Set API_SECRET_KEY in your .env file for production use."
        )
        return _DEV_SECRET_KEY

    # CORS Configuration
    api_cors_origins: str = "*"

    # Rate Limiting (requests per minute)
    api_rate_limit: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if self.api_cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.api_cors_origins.split(",")]


# Global API settings instance
api_settings = APISettings()
