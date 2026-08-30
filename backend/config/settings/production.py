"""
Django production settings for Junkbin.io

Settings optimized for production deployment.
"""
import sys

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Always allow localhost and backend for health checks and internal communication
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[]) + ['localhost', 'backend', '127.0.0.1']

# CORS - Restrict to specific origins
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['https://junkbin.io', 'https://www.junkbin.io'])
CORS_ALLOW_CREDENTIALS = True

# CSRF - Required for Django 4.0+ with HTTPS
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['https://junkbin.io', 'https://www.junkbin.io'])

# =============================================================================
# Security Settings
# =============================================================================
# SECURE_SSL_REDIRECT can be disabled for local Docker testing without SSL
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS Settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Cross-Origin Isolation Headers
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Content Security Policy (via django-csp 4.0+)
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://accounts.google.com/gsi/client"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://accounts.google.com/gsi/style"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "https://accounts.google.com"],
        "frame-src": ["https://accounts.google.com"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
        "upgrade-insecure-requests": env.bool("CSP_UPGRADE_INSECURE", default=True),
    }
}

# Permissions Policy - explicitly disable unnecessary browser features
PERMISSIONS_POLICY = {
    'accelerometer': [],
    'ambient-light-sensor': [],
    'autoplay': [],
    'battery': [],
    'camera': [],
    'cross-origin-isolated': [],
    'display-capture': [],
    'document-domain': [],
    'encrypted-media': [],
    'execution-while-not-rendered': [],
    'execution-while-out-of-viewport': [],
    'fullscreen': [],
    'geolocation': [],
    'gyroscope': [],
    'keyboard-map': [],
    'magnetometer': [],
    'microphone': [],
    'midi': [],
    'navigation-override': [],
    'payment': [],
    'picture-in-picture': [],
    'publickey-credentials-get': [],
    'screen-wake-lock': [],
    'sync-xhr': [],
    'usb': [],
    'web-share': [],
    'xr-spatial-tracking': [],
}

# =============================================================================
# Email Configuration (Production)
# =============================================================================
EMAIL_HOST = env('EMAIL_HOST', default='')

if EMAIL_HOST:
    # SMTP configured - use real email
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@junkbin.io')
    SERVER_EMAIL = env('SERVER_EMAIL', default='errors@junkbin.io')
    # Require email verification when SMTP is configured
    ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
else:
    # No SMTP configured - use console backend (prints to logs)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'noreply@junkbin.io'
    SERVER_EMAIL = 'errors@junkbin.io'
    # Skip email verification when no SMTP
    ACCOUNT_EMAIL_VERIFICATION = 'optional'

# =============================================================================
# Database Connection Pooling
# =============================================================================
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# =============================================================================
# Caching (Redis in production)
# =============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
    }
}

# Session backend: cached_db persists to DB if Redis evicts the key,
# preventing admin logouts on Redis restart or memory pressure.
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_SAVE_EVERY_REQUEST = True  # Refresh TTL on every admin request

# =============================================================================
# Static Files (Production)
# =============================================================================
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# Sentry Error Tracking
# =============================================================================
SENTRY_DSN = env('SENTRY_DSN', default='')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            # Free Sentry plan includes exactly 1 cron monitor. check-system-health
            # runs every 5 minutes, so a missed check-in catches celery-beat dying
            # entirely (which silently kills all 4 scheduled tasks) faster than
            # monitoring any single less-frequent task would. The other 3 stay
            # excluded rather than spending money on additional monitors
            # ($0.78/mo each) for a hobby-scale deployment.
            CeleryIntegration(
                monitor_beat_tasks=True,
                exclude_beat_tasks=[
                    'send-daily-digest',
                    'cleanup-search-queries',
                    'cleanup-old-activity',
                ],
            ),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        # Both dev and prod run this same settings module (config.settings.production)
        # - hardcoding 'production' here would mislabel dev's traffic in Sentry as
        # real prod events under the same DSN.
        environment=env('SENTRY_ENVIRONMENT', default='production'),
        # Baked into the image at build time (see backend/Dockerfile) so events
        # can be tied to the deploy that produced them - lets Sentry show which
        # release introduced a regression instead of one undifferentiated pool.
        release=env('GIT_SHA', default=None),
    )

# =============================================================================
# Logging (Production)
# =============================================================================
# Docker's json-file driver discards a container's captured stdout the moment
# it's recreated (a routine part of every deploy), so console-only logging
# leaves nothing to debug after the next `docker compose up`. Mirror it to a
# file on the backend_logs volume, which survives container recreation.
#
# gunicorn (backend), celery worker, and celery-beat all load this same
# settings module but must not share one log file - concurrent processes
# rotating/writing the same path can interleave or clobber each other. Derive
# a per-service filename from how the process was invoked instead of adding
# more docker-compose plumbing.
if 'beat' in sys.argv:
    _SERVICE_NAME = 'celery-beat'
elif 'celery' in sys.argv[0]:
    _SERVICE_NAME = 'celery'
else:
    _SERVICE_NAME = 'backend'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            # Not RotatingFileHandler: rotation isn't safe across the multiple
            # processes (gunicorn workers) that write this same file, and
            # plain append() calls are. Bound growth with logrotate instead
            # (see deployment/logrotate/junkbin).
            'class': 'logging.FileHandler',
            'filename': f'/app/logs/{_SERVICE_NAME}.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# Rate Limiting (Stricter in production)
# =============================================================================
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '300/hour',
    'user': '1000/hour',
    'auth': '5/minute',
    'submission': '10/hour',
    'upload': '60/hour',
    'report': '10/hour',
    'search': '60/minute',
    'messaging': '30/minute',
    'polling': '120/minute',
    'lookup': '20/hour',
    'subscribe': '10/hour',
    'bg_removal': '40/hour',
}

# =============================================================================
# Admin Security
# =============================================================================
# Add admin IP whitelist middleware in production
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware') + 1,
    'apps.api.middleware.AdminIPWhitelistMiddleware'
)

# =============================================================================
# JWT Cookie Security (Production)
# =============================================================================
SIMPLE_JWT['AUTH_COOKIE_SECURE'] = env.bool('AUTH_COOKIE_SECURE', default=True)
