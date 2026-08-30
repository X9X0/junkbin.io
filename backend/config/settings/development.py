"""
Django development settings for Junkbin.io

Settings for local development environment.
"""
import os

# Development SECRET_KEY - NEVER use in production
# This must be set BEFORE importing base to satisfy the requirement
os.environ.setdefault('SECRET_KEY', 'dev-insecure-key-for-local-development-only-abc123xyz789')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Use SQLite for development (no PostgreSQL required)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Disable SSL/HTTPS requirements in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use console email backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable email verification for easier testing
ACCOUNT_EMAIL_VERIFICATION = 'optional'

# Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}

# Use local file storage in development
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Simplified caching for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable throttling in development (keep rate keys defined to avoid
# ImproperlyConfigured — several views instantiate throttle classes directly
# via get_throttles()/throttle_classes, bypassing DEFAULT_THROTTLE_CLASSES)
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/hour',
    'user': '1000/hour',
    'auth': '1000/hour',
    'submission': '1000/hour',
    'upload': '1000/hour',
    'report': '1000/hour',
    'search': '1000/hour',
    'messaging': '1000/hour',
    'polling': '1000/hour',
    'lookup': '1000/hour',
    'subscribe': '10/hour',
    'bg_removal': '1000/hour',
}

# Logging
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'

# Static files - development mode
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
