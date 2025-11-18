"""
Django settings for habit_reward_project.

Generated for habit reward bot migration from Airtable to Django.
"""

import os
from pathlib import Path
import environ

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, True),
    DATABASE_URL=(str, f'sqlite:///{BASE_DIR}/db.sqlite3'),
    SECRET_KEY=(str, 'django-insecure-development-key-CHANGE-IN-PRODUCTION'),
)

# Read .env file if it exists (skip during pytest to use test database)
env_file = BASE_DIR / '.env'
if env_file.exists() and not os.environ.get('PYTEST_RUNNING'):
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '[::1]'])

# CSRF Configuration for webhooks
# Required for Django 4.0+ when using HTTPS webhooks in production
# In production, set this to your domain (e.g., https://yourdomain.com)
# For development (localhost), leave empty - not needed
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'src.core',  # Core models for habit reward system
]

# Custom User Model
# Must be set before any migrations are created
AUTH_USER_MODEL = 'core.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src.habit_reward_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'src.habit_reward_project.wsgi.application'
ASGI_APPLICATION = 'src.habit_reward_project.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for serving static files
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# CUSTOM SETTINGS FOR HABIT REWARD BOT
# =============================================================================

# Airtable Configuration (kept for fallback)
AIRTABLE_API_KEY = env('AIRTABLE_API_KEY', default='test_key')
AIRTABLE_BASE_ID = env('AIRTABLE_BASE_ID', default='test_base')

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='test_token')
TELEGRAM_WEBHOOK_URL = env('TELEGRAM_WEBHOOK_URL', default=None)

# LLM Configuration
LLM_PROVIDER = env('LLM_PROVIDER', default='openai')  # e.g., "openai", "anthropic", "ollama"
LLM_MODEL = env('LLM_MODEL', default='gpt-3.5-turbo')  # e.g., "gpt-4", "claude-3-sonnet"
LLM_API_KEY = env('LLM_API_KEY', default=None)  # API key for the LLM provider

# Optional: Default User Configuration
DEFAULT_USER_TELEGRAM_ID = env('DEFAULT_USER_TELEGRAM_ID', default=None)

# Gamification Configuration
STREAK_MULTIPLIER_RATE = env.float('STREAK_MULTIPLIER_RATE', default=0.1)
PROGRESS_BAR_LENGTH = env.int('PROGRESS_BAR_LENGTH', default=10)
RECENT_LOGS_LIMIT = env.int('RECENT_LOGS_LIMIT', default=10)

# Logging Configuration
LOG_LEVEL = env('LOG_LEVEL', default='INFO')
LOG_FORMAT = env('LOG_FORMAT', default='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Internationalization Configuration
SUPPORTED_LANGUAGES = env.list('SUPPORTED_LANGUAGES', default=['en', 'ru', 'kk'])
DEFAULT_LANGUAGE = env('DEFAULT_LANGUAGE', default='en')

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
HABIT_WEIGHT_MIN = 1
HABIT_WEIGHT_MAX = 100


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'src': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
