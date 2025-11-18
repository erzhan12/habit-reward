"""Test settings for habit_reward_project - uses SQLite instead of PostgreSQL."""

from .settings import *  # noqa: F403

# Override database to use SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
