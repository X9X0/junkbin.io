"""
Django test settings for Junkbin.io

Settings optimized for running tests.
"""
import os

# Test SECRET_KEY - only used in tests
os.environ.setdefault('SECRET_KEY', 'test-insecure-key-for-testing-only-never-use-in-production')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

from .base import *

DEBUG = False

# Use faster password hasher for tests
# NOTE: MD5 is intentionally used here for TEST SPEED ONLY.
# This is NOT secure for production - it's only acceptable in tests
# where password hashing happens frequently and security is not a concern.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable throttling in tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Use console email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable email verification for tests
ACCOUNT_EMAIL_VERIFICATION = 'none'

# Use local file storage
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Disable Celery in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Logging - minimal output during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}
