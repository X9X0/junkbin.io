"""
Django base settings for Junkbin.io

Common settings shared across all environments.
"""
import os
from pathlib import Path
from datetime import timedelta

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
# No default - SECRET_KEY must be explicitly set in environment
SECRET_KEY = env('SECRET_KEY')

# Application definition
DJANGO_APPS = [
    'config.admin.JunkbinAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django_celery_beat',
    'django_celery_results',
    'django_prometheus',
    'imagekit',
    'storages',
    'axes',
    'import_export',
]

LOCAL_APPS = [
    'apps.users',
    'apps.products',
    'apps.components',
    'apps.submissions',
    'apps.reports',
    'apps.api',
    'apps.newsletter',
    'apps.messaging',
    'apps.junkbin',
    'apps.recipes',
    'apps.webhooks',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# No default - DATABASE_URL must be explicitly set in environment
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('pt', 'Portuguese'),
    ('de', 'German'),
    ('it', 'Italian'),
    ('nl', 'Dutch'),
    ('pl', 'Polish'),
    ('cs', 'Czech'),
    ('sk', 'Slovak'),
    ('hr', 'Croatian'),
    ('sr', 'Serbian'),
    ('sl', 'Slovenian'),
    ('ru', 'Russian'),
    ('uk', 'Ukrainian'),
    ('ro', 'Romanian'),
    ('hu', 'Hungarian'),
    ('tr', 'Turkish'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Upload size limits (10 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sites framework
SITE_ID = 1

# Frontend URL for password reset links
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:5173')

# Admin URL (can be obfuscated for security)
ADMIN_URL = env('ADMIN_URL', default='admin/')

# Admin IP whitelist (empty = allow all, for development)
# Example: ADMIN_ALLOWED_IPS=10.0.0.1,192.168.1.0/24
ADMIN_ALLOWED_IPS = env.list('ADMIN_ALLOWED_IPS', default=[])

# =============================================================================
# Django REST Framework
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.users.authentication.CookieJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.api.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '5/minute',
        'submission': '50/hour',
        'report': '10/hour',
        'search': '60/minute',
        'messaging': '30/minute',
        'lookup': '20/hour',
    },
}

# =============================================================================
# Simple JWT
# =============================================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # HttpOnly cookie settings for XSS protection
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_SECURE': False,  # Overridden to True in production.py
    'AUTH_COOKIE_HTTP_ONLY': True,  # Not accessible via JavaScript
    'AUTH_COOKIE_SAMESITE': 'Lax',  # CSRF protection
    'AUTH_COOKIE_PATH': '/',
}

# =============================================================================
# DRF Spectacular (API Documentation)
# =============================================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Junkbin.io API',
    'DESCRIPTION': 'Community-driven e-waste component database API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'auth', 'description': 'Authentication endpoints'},
        {'name': 'users', 'description': 'User management'},
        {'name': 'products', 'description': 'Product documentation'},
        {'name': 'components', 'description': 'Electronic components'},
        {'name': 'submissions', 'description': 'Content submissions'},
        {'name': 'reports', 'description': 'User reports'},
        {'name': 'search', 'description': 'Search functionality'},
        {'name': 'messaging', 'description': 'User-to-user messaging'},
    ],
}

# =============================================================================
# Django Import/Export
# =============================================================================
IMPORT_EXPORT_USE_TRANSACTIONS = True

# =============================================================================
# Django Allauth
# =============================================================================
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/api/auth/login/'

# Google OAuth Client ID (used by GoogleAuthView for ID token verification)
OAUTH_GOOGLE_CLIENT_ID = env('OAUTH_GOOGLE_CLIENT_ID', default='')

# GitHub OAuth credentials (used by GitHubAuthView for code exchange)
OAUTH_GITHUB_CLIENT_ID = env('OAUTH_GITHUB_CLIENT_ID', default='')
OAUTH_GITHUB_CLIENT_SECRET = env('OAUTH_GITHUB_CLIENT_SECRET', default='')

# Social Account Providers
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': env('OAUTH_GOOGLE_CLIENT_ID', default=''),
            'secret': env('OAUTH_GOOGLE_CLIENT_SECRET', default=''),
        }
    }
}

# =============================================================================
# Django Axes (Brute Force Protection)
# =============================================================================
AXES_FAILURE_LIMIT = 5  # Lock out after 5 failed attempts
AXES_COOLOFF_TIME = 1  # Lock out for 1 hour (in hours)
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # Lock by username + IP combo
AXES_RESET_ON_SUCCESS = True  # Reset failed attempts on successful login
AXES_LOCKOUT_CALLABLE = 'apps.api.middleware.axes_lockout_response'  # Custom lockout message
AXES_ENABLE_ACCESS_FAILURE_LOG = True  # Persist failed login attempts in AccessFailureLog
AXES_IPWARE_PROXY_COUNT = 0  # nginx appends the real client IP to XFF; take rightmost entry
AXES_IPWARE_META_PRECEDENCE_ORDER = [
    'HTTP_X_FORWARDED_FOR',
    'REMOTE_ADDR',
]

# =============================================================================
# Celery Configuration
# =============================================================================
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'check-system-health': {
        'task': 'apps.api.tasks.check_system_health',
        'schedule': 300.0,  # every 5 minutes
    },
    'send-daily-digest': {
        'task': 'apps.api.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),  # 8 AM Eastern
    },
    'cleanup-search-queries': {
        'task': 'apps.api.tasks.cleanup_old_search_queries',
        'schedule': crontab(hour=3, minute=0),
    },
    'cleanup-old-activity': {
        'task': 'apps.api.tasks.cleanup_old_activity',
        'schedule': crontab(hour=3, minute=30),
    },
}

# =============================================================================
# Caching
# =============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
    }
}

# =============================================================================
# Email Configuration
# =============================================================================
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@junkbin.io')

# =============================================================================
# File Storage
# =============================================================================
STORAGE_BACKEND = env('STORAGE_BACKEND', default='local')

if STORAGE_BACKEND == 's3':
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# =============================================================================
# Image Processing
# =============================================================================
IMAGEKIT_DEFAULT_CACHEFILE_STRATEGY = 'imagekit.cachefiles.strategies.Optimistic'
IMAGEKIT_CACHEFILE_DIR = 'cache'

# Maximum upload sizes
MAX_IMAGE_SIZE_MB = env.int('MAX_IMAGE_SIZE_MB', default=10)
MAX_IMAGE_SIZE = MAX_IMAGE_SIZE_MB * 1024 * 1024  # Convert to bytes
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

# =============================================================================
# Junkbin-Specific Settings
# =============================================================================

# Moderation settings
REPORT_STRIKE_THRESHOLD = 3  # Number of reports before automatic review
TRUSTED_USER_CONTRIBUTION_THRESHOLD = 25  # Contributions needed for trusted status
TRUSTED_USER_MIN_REPUTATION = 50  # Minimum reputation for trusted status

# Voting settings
VERIFICATION_VOTE_THRESHOLD = 3   # Net vote score needed for auto-verification
DISPUTE_REVIEW_THRESHOLD = -2     # Net vote score that triggers needs_review
TRUSTED_USER_VOTE_WEIGHT = 2      # Vote weight for trusted users / moderators
VOTE_REPUTATION_BONUS = 1         # Reputation bonus for confirm voters on auto-verify

# Messaging settings
MESSAGE_MAX_LENGTH = 5000  # Max characters per message

# Submission settings
SUBMISSION_LEVELS = [
    ('basic', 'Basic (Major Components Only)'),
    ('advanced', 'Advanced (Complete BOM)'),
]

# Component types
COMPONENT_TYPES = [
    # Active components
    ('ic', 'Integrated Circuit'),
    ('mcu', 'Microcontroller'),
    ('transistor', 'Transistor'),
    ('mosfet', 'MOSFET'),
    ('diode', 'Diode'),
    ('regulator', 'Voltage Regulator'),
    ('opamp', 'Op-Amp'),
    # Passive components
    ('resistor', 'Resistor'),
    ('capacitor', 'Capacitor'),
    ('inductor', 'Inductor'),
    ('transformer', 'Transformer'),
    ('crystal', 'Crystal/Oscillator'),
    ('fuse', 'Fuse'),
    ('ferrite', 'Ferrite Bead'),
    # Electromechanical
    ('relay', 'Relay'),
    ('switch', 'Switch'),
    ('connector', 'Connector'),
    ('socket', 'Socket/Header'),
    # RF/Wireless
    ('antenna', 'Antenna'),
    ('rf_module', 'RF Module'),
    ('balun', 'Balun/Filter'),
    # Power
    ('battery', 'Battery/Cell'),
    ('power_jack', 'Power Jack/Barrel'),
    ('usb_port', 'USB Port'),
    # Display/Output
    ('led', 'LED'),
    ('display', 'Display/LCD'),
    ('speaker', 'Speaker/Buzzer'),
    # Sensors
    ('sensor', 'Sensor'),
    ('thermistor', 'Thermistor/NTC'),
    # Modules & Assemblies
    ('module', 'Module/Daughter Board'),
    ('pcb_assembly', 'PCB Assembly'),
    # Cabling & Wiring
    ('cable', 'Cable/Wire Harness'),
    ('flex_cable', 'Flex Cable/FPC'),
    ('coax', 'Coaxial Cable'),
    # Other
    ('heatsink', 'Heatsink'),
    ('shield', 'EMI Shield'),
    ('mechanical', 'Mechanical Part'),
    ('other', 'Other'),
]

# Product categories
PRODUCT_CATEGORIES = [
    # Computing
    ('desktop', 'Desktop Computer'),
    ('laptop', 'Laptop/Notebook'),
    ('tablet', 'Tablet'),
    ('server', 'Server'),
    ('sbc', 'Single Board Computer'),
    # Mobile
    ('phone', 'Smartphone'),
    ('feature_phone', 'Feature Phone'),
    ('pager', 'Pager/Beeper'),
    # Display
    ('tv', 'Television'),
    ('monitor', 'Monitor'),
    ('projector', 'Projector'),
    # Networking
    ('router', 'Router'),
    ('modem', 'Modem'),
    ('switch', 'Network Switch'),
    ('access_point', 'Access Point'),
    ('extender', 'Range Extender'),
    # Audio/Video
    ('audio', 'Audio Equipment'),
    ('speaker', 'Speaker/Soundbar'),
    ('headphones', 'Headphones/Earbuds'),
    ('camera', 'Camera'),
    ('camcorder', 'Camcorder'),
    ('dvr', 'DVR/NVR'),
    ('streaming', 'Streaming Device'),
    # Gaming
    ('gaming', 'Gaming Console'),
    ('handheld', 'Handheld Gaming'),
    ('controller', 'Game Controller'),
    # Peripherals
    ('keyboard', 'Keyboard'),
    ('mouse', 'Mouse'),
    ('printer', 'Printer'),
    ('scanner', 'Scanner'),
    ('webcam', 'Webcam'),
    # Remote Controls
    ('remote', 'Remote Control'),
    ('universal_remote', 'Universal Remote'),
    # Power
    ('power_supply', 'Power Supply/Adapter'),
    ('ups', 'UPS/Battery Backup'),
    ('charger', 'Charger'),
    ('power_strip', 'Power Strip/Surge Protector'),
    # Storage
    ('hdd', 'Hard Drive'),
    ('ssd', 'SSD'),
    ('nas', 'NAS'),
    ('usb_drive', 'USB Drive'),
    # Home Automation
    ('iot', 'IoT Device'),
    ('smart_home', 'Smart Home Hub'),
    ('thermostat', 'Smart Thermostat'),
    ('doorbell', 'Smart Doorbell'),
    ('security_cam', 'Security Camera'),
    # Appliances
    ('appliance', 'Home Appliance'),
    ('hvac', 'HVAC/Climate Control'),
    ('kitchen', 'Kitchen Appliance'),
    # Automotive
    ('automotive', 'Automotive Electronics'),
    ('dashcam', 'Dash Camera'),
    ('gps', 'GPS/Navigation'),
    ('obd', 'OBD Device'),
    # Specialized
    ('medical', 'Medical Device'),
    ('industrial', 'Industrial Equipment'),
    ('test_equipment', 'Test Equipment'),
    ('radio', 'Radio/Transceiver'),
    ('drone', 'Drone/UAV'),
    # Other
    ('other', 'Other'),
]

# Region codes
REGIONS = [
    ('us', 'United States'),
    ('eu', 'European Union'),
    ('uk', 'United Kingdom'),
    ('jp', 'Japan'),
    ('cn', 'China'),
    ('kr', 'South Korea'),
    ('tw', 'Taiwan'),
    ('au', 'Australia'),
    ('ca', 'Canada'),
    ('global', 'Global/Universal'),
    ('other', 'Other'),
]

# =============================================================================
# External API Keys
# =============================================================================

# Nexar (Octopart) API — component pricing, availability, datasheets
NEXAR_CLIENT_ID = env('NEXAR_CLIENT_ID', default='')
NEXAR_CLIENT_SECRET = env('NEXAR_CLIENT_SECRET', default='')

# Site URL for webhook embeds
SITE_URL = env('SITE_URL', default='http://localhost:8000')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
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
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
