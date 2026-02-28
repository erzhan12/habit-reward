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

# Base allowed hosts (can be extended by NGROK_URL)
ALLOWED_HOSTS_BASE = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '[::1]'])

# CSRF Configuration for webhooks
# Required for Django 4.0+ when using HTTPS webhooks in production
# In production, set this to your domain (e.g., https://yourdomain.com)
# For development (localhost), leave empty - not needed
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# HTTPS enforcement and session security in production.
# These settings are critical for protecting against MITM, session hijacking,
# and cross-site attacks.  Only applied when DEBUG=False.
if not DEBUG:
    # Redirect all HTTP requests to HTTPS (prevents accidental plaintext traffic).
    SECURE_SSL_REDIRECT = True
    # Trust the X-Forwarded-Proto header from the reverse proxy (nginx/Caddy)
    # to detect HTTPS.  Required when SSL terminates at the proxy, not Django.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Only send session cookie over HTTPS (prevents session theft via HTTP).
    SESSION_COOKIE_SECURE = True
    # Only send CSRF cookie over HTTPS (prevents CSRF token theft via HTTP).
    CSRF_COOKIE_SECURE = True
    # HTTP Strict Transport Security: browsers remember to use HTTPS for 1 year,
    # preventing SSL-stripping attacks on subsequent visits.
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    # Apply HSTS to all subdomains (prevents subdomain-based downgrade attacks).
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Allow browsers to preload this site's HSTS policy (hstspreload.org).
    SECURE_HSTS_PRELOAD = True

    # Session cookie hardening: timeout, no JS access, SameSite
    SESSION_COOKIE_AGE = 1209600  # 2 weeks
    # Prevent JavaScript from reading the session cookie (mitigates XSS-based
    # session theft).
    SESSION_COOKIE_HTTPONLY = True
    # SameSite=Lax: cookie is sent on top-level navigations but not on
    # cross-site sub-requests, preventing most CSRF attacks.
    SESSION_COOKIE_SAMESITE = "Lax"

    # CSRF cookie SameSite (HttpOnly omitted: Inertia/axios reads XSRF-TOKEN; see RULES.md)
    CSRF_COOKIE_SAMESITE = "Lax"


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'src.core',  # Core models for habit reward system
    'django_vite',  # Vite asset integration
    'inertia',  # Inertia.js server adapter
]

# Custom User Model
# Must be set before any migrations are created
AUTH_USER_MODEL = 'core.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'src.web.middleware.ContentSecurityPolicyMiddleware',  # CSP headers
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'src.web.middleware.WebAuthMiddleware',  # Web login redirect
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'src.web.middleware.InertiaFlashMiddleware',  # Django messages → Inertia flash props
    'inertia.middleware.InertiaMiddleware',  # Inertia.js protocol
]

ROOT_URLCONF = 'src.habit_reward_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'src' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'src.web.context_processors.csp_nonce',
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

# Reuse database connections for 10 minutes instead of closing after each
# request. This reduces connection overhead in ThreadPoolExecutor workers
# for PostgreSQL/MySQL.
# NOTE: SQLite ignores CONN_MAX_AGE (no connection pooling benefit).
# NOTE: Tune based on thread pool size - with 10 workers, you need at least
# 10 DB connections available on PostgreSQL/MySQL.
DATABASES['default']['CONN_MAX_AGE'] = env.int('CONN_MAX_AGE', default=600)


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
STATICFILES_DIRS = [BASE_DIR / 'frontend' / 'dist']

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

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='test_token')

# Webhook URL: Use NGROK_URL if set (for development), otherwise use explicit TELEGRAM_WEBHOOK_URL
NGROK_URL = env('NGROK_URL', default=None)
if NGROK_URL and NGROK_URL.strip():
    # Derive webhook URL from ngrok URL
    TELEGRAM_WEBHOOK_URL = f"{NGROK_URL.rstrip('/')}/webhook/telegram"
    # Extract domain and add to ALLOWED_HOSTS
    import re
    ngrok_domain = re.sub(r'https?://', '', NGROK_URL).split('/')[0]
    # Combine base hosts with ngrok domain
    ALLOWED_HOSTS = list(ALLOWED_HOSTS_BASE)
    if ngrok_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(ngrok_domain)
else:
    # Use explicit webhook URL if NGROK_URL is not set
    TELEGRAM_WEBHOOK_URL = env('TELEGRAM_WEBHOOK_URL', default=None)
    ALLOWED_HOSTS = ALLOWED_HOSTS_BASE

# LLM Configuration
NLP_ENABLED = env.bool('NLP_ENABLED', default=False)  # Set to True to enable NLP/AI features
LLM_PROVIDER = env('LLM_PROVIDER', default='openai')  # e.g., "openai", "anthropic", "ollama"
LLM_MODEL = env('LLM_MODEL', default='gpt-3.5-turbo')  # e.g., "gpt-4", "claude-3-sonnet"
LLM_API_KEY = env('LLM_API_KEY', default=None)  # API key for the LLM provider

# Optional: Default User Configuration
DEFAULT_USER_TELEGRAM_ID = env('DEFAULT_USER_TELEGRAM_ID', default=None)

# Gamification Configuration
STREAK_MULTIPLIER_RATE = env.float('STREAK_MULTIPLIER_RATE', default=0.1)
PROGRESS_BAR_LENGTH = env.int('PROGRESS_BAR_LENGTH', default=10)
RECENT_LOGS_LIMIT = env.int('RECENT_LOGS_LIMIT', default=10)
NO_REWARD_PROBABILITY_PERCENT = env.float('NO_REWARD_PROBABILITY_PERCENT', default=50.0)

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

# Web auth rate limit (django-ratelimit format, e.g. '10/m', '5/m')
AUTH_RATE_LIMIT = env('AUTH_RATE_LIMIT', default='10/m')
# Status polling rate limit (higher than auth because polling is frequent)
AUTH_STATUS_RATE_LIMIT = env('AUTH_STATUS_RATE_LIMIT', default='30/m')
# Dashboard actions (complete/revert habit) rate limit per user
DASHBOARD_ACTION_RATE_LIMIT = env('DASHBOARD_ACTION_RATE_LIMIT', default='60/m')

# Thread pool size for background login processing (DB writes + Telegram send).
# Default 10: balances concurrency with SQLite's file-level write lock.
# Each worker blocks for a Telegram API round-trip (~200ms-2s).  10 workers
# can handle ~5-50 concurrent logins depending on API latency.
# For PostgreSQL: can increase to 50-100.
# For SQLite: keep at 10 max due to write lock contention.
# Monitor 503 errors to detect if this needs tuning.
WEB_LOGIN_THREAD_POOL_SIZE = env.int('WEB_LOGIN_THREAD_POOL_SIZE', default=10)

# Login request expiry in minutes (how long users have to confirm in Telegram).
# Must stay in sync with frontend LOGIN_EXPIRY_MS in Login.vue.
WEB_LOGIN_EXPIRY_MINUTES = env.int('WEB_LOGIN_EXPIRY_MINUTES', default=5)

# Trust X-Forwarded-For header for client IP detection.
# Only enable when Django is behind a trusted reverse proxy (e.g. nginx/Caddy)
# that overwrites X-Forwarded-For with the real client IP.
TRUST_X_FORWARDED_FOR = env.bool('TRUST_X_FORWARDED_FOR', default=False)

# Number of consecutive cache write failures before the CacheManager raises
# CacheWriteError (circuit breaker).  High enough to tolerate transient blips
# (e.g. Redis failover ~1-5s), low enough to surface genuine misconfiguration.
# See src/web/services/web_login_service/cache_operations.py.
CACHE_FAILURE_THRESHOLD = env.int('CACHE_FAILURE_THRESHOLD', default=5)


# =============================================================================
# INERTIA.JS + VITE CONFIGURATION
# =============================================================================

INERTIA_LAYOUT = 'base.html'

DJANGO_VITE = {
    'default': {
        'dev_mode': DEBUG,
        'dev_server_host': env('DJANGO_VITE_DEV_SERVER_HOST', default='localhost'),
        'dev_server_port': env.int('DJANGO_VITE_DEV_SERVER_PORT', default=5173),
    }
}


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
