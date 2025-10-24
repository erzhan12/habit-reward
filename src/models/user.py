"""User model representing users in the system."""

from pydantic import BaseModel, Field, field_validator, ConfigDict


class User(BaseModel):
    """User model with telegram_id as primary identifier."""

    id: str | None = None  # Airtable record ID
    telegram_id: str = Field(..., description="Unique Telegram user ID")
    name: str = Field(..., description="User display name")
    is_active: bool = Field(default=False, description="Whether user is active (default False for security)")
    language: str = Field(default='en', description="User's preferred language (ISO 639-1 code)")

    @field_validator('telegram_id', mode='before')
    @classmethod
    def convert_telegram_id_to_string(cls, v):
        """Convert telegram_id to string if it's an integer."""
        if isinstance(v, int):
            return str(v)
        return v

    @field_validator('is_active', mode='before')
    @classmethod
    def handle_airtable_checkbox(cls, v):
        """Handle Airtable checkbox behavior.

        When Airtable checkboxes are unchecked, the field is not included in
        API responses (or returns None). We explicitly convert None to False
        to ensure proper handling of inactive users.
        """
        if v is None:
            return False
        return v

    @field_validator('language', mode='before')
    @classmethod
    def validate_language_code(cls, v):
        """Validate and normalize language code to lowercase ISO 639-1 format."""
        if v is None:
            return 'en'
        return str(v).lower()[:2]  # Ensure 2-letter lowercase code

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "telegram_id": "123456789",
                "name": "John Doe",
                "is_active": True,
                "language": "en"
            }
        }
    )
