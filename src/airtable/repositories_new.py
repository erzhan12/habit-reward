"""Repository imports for backward compatibility."""

# Import all repositories from their separate files
from src.airtable.user_repository import user_repository
from src.airtable.habit_repository import habit_repository  
from src.airtable.reward_repository import reward_repository

# Import remaining repositories from original file temporarily
from src.airtable.repositories import (
    reward_progress_repository,
    habit_log_repository
)

# Re-export for backward compatibility
__all__ = [
    'user_repository',
    'habit_repository', 
    'reward_repository',
    'reward_progress_repository',
    'habit_log_repository'
]
