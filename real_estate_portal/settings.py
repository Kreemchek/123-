import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
from urllib.parse import urlparse, unquote

load_dotenv()

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

# Debug must be controlled by env in production
DEBUG = env_bool("DEBUG", False)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-local-development-key-change-in-production-123456789')

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
    'SECURE': True,
    'STATIC_IMAGES': False,
    'MEDIA_TAG': 'media',
    'EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS': (),
    'STATICFILES_MIMETYPES': {
        'txt': 'text/plain',
        'html': 'text/html',
        'css': 'text/css',
        'js': 'application/javascript',
        'json': 'application/json',
        'xml': 'application/xml',
        'swf': 'application/x-shockwave-flash',
        'flv': 'video/x-flv',
        'png': 'image/png',
        'jpe': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'ico': 'image/vnd.microsoft.icon',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
        'svg': 'image/svg+xml',
        'svgz': 'image/svg+xml',
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
}

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

handler500 = 'accounts.views.server_error'

# Allowed hosts from environment
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        'ALLOWED_HOSTS',
        '89.169.168.72,localhost,127.0.0.1,192.168.1.98,winwindeal.ru,www.winwindeal.ru,winwindeal.store,www.winwindeal.store,winwindeal-test.loca.lt,sara-tea-promotion-pharmaceutical.trycloudflare.com,complement-constant-week-charged.trycloudflare.com,coming-designated-lights-previous.trycloudflare.com,levels-west-recruitment-mixing.trycloudflare.com,subcommittee-occupied-description-nil.trycloudflare.com,depending-tar-category-among.trycloudflare.com,divide-sentences-gps-clothing.trycloudflare.com',
    ).split(',')
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    # Домены
    'https://winwindeal.ru',
    'https://www.winwindeal.ru',
    'http://winwindeal.ru',
    'http://www.winwindeal.ru',
    'https://winwindeal.store',
    'https://www.winwindeal.store',
    'http://winwindeal.store',
    'http://www.winwindeal.store',
    # IP/туннели (если используются)
    'https://89.169.168.72',
    'http://89.169.168.72',
    'https://winwindeal-test.loca.lt',
    'http://winwindeal-test.loca.lt',
    'https://sara-tea-promotion-pharmaceutical.trycloudflare.com',
    'https://complement-constant-week-charged.trycloudflare.com',
    'https://coming-designated-lights-previous.trycloudflare.com',
    'https://levels-west-recruitment-mixing.trycloudflare.com',
    'https://subcommittee-occupied-description-nil.trycloudflare.com',
    'https://tricks-entirely-retreat-reggae.trycloudflare.com',
    'https://depending-tar-category-among.trycloudflare.com',
    'https://divide-sentences-gps-clothing.trycloudflare.com',
]

_csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS")
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(",") if o.strip()]

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS = [
    'cloudinary',
    'cloudinary_storage',
    'accounts.apps.AccountsConfig',
    'brokers.apps.BrokersConfig',
    'developers.apps.DevelopersConfig',
    'clients.apps.ClientsConfig',
    'properties.apps.PropertiesConfig',
    'payments.apps.PaymentsConfig',
    'media_content.apps.MediaContentConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # Re-enabled for SpatiaLite
    'django_filters',
    'widget_tweaks',
    'channels',
    'corsheaders',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'brokers.middleware.BrokerProfileCompletionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.ActivityLoggerMiddleware',
    'accounts.middleware.ProfileCompletionMiddleware',
]

ROOT_URLCONF = 'real_estate_portal.urls'

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
                'django.template.context_processors.media',
                'accounts.context_processors.subscriptions',
            ],
        },
    },
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'geocode.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'properties': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

WSGI_APPLICATION = 'real_estate_portal.wsgi.application'

# Database configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    scheme = (parsed.scheme or "").lower()
    if scheme in {"postgres", "postgresql", "postgis"}:
        DATABASES = {
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.postgis",
                "NAME": unquote((parsed.path or "").lstrip("/")),
                "USER": unquote(parsed.username or ""),
                "PASSWORD": unquote(parsed.password or ""),
                "HOST": parsed.hostname or "",
                "PORT": str(parsed.port or ""),
                "CONN_MAX_AGE": int(os.getenv("CONN_MAX_AGE", "60")),
            }
        }
    elif scheme in {"sqlite", "spatialite"}:
        db_path = (parsed.path or "").lstrip("/") or "db.sqlite3"
        DATABASES = {
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.spatialite",
                "NAME": str(BASE_DIR / db_path),
            }
        }
    else:
        # Unknown scheme: fall back to local SQLite/SpatiaLite
        DATABASES = {
            "default": {
                "ENGINE": "django.contrib.gis.db.backends.spatialite",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'accounts.backends.EmailVerifiedBackend',
]

FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_MAX_MEMORY_SIZE = 10*1024*1024

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = False
USE_TZ = True
DECIMAL_SEPARATOR = '.'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
WHITENOISE_MAX_AGE = 86400

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static files settings
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Django 5+: use STORAGES instead of legacy DEFAULT_FILE_STORAGE/STATICFILES_STORAGE
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # Use manifest storage so Django resolves hashed admin/static asset names
        # (we deploy prebuilt `staticfiles/` with `staticfiles.json`).
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

AUTH_USER_MODEL = 'accounts.User'

LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# Email configuration from environment
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.yandex.ru')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'goldinpav@yandex.ru')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'WinWinDeal <goldinpav@yandex.ru>')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Yoomoney from environment
YOOMONEY_ACCOUNT_ID = os.getenv('YOOMONEY_ACCOUNT_ID', '1105130')
YOOMONEY_SECRET_KEY = os.getenv('YOOMONEY_SECRET_KEY', '')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

class OwnerAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)

# Security settings from environment
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)

# Static files finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Yandex APIs from environment
YANDEX_MAPS_API_KEY = os.getenv('YANDEX_MAPS_API_KEY', '')
YANDEX_GEOCODER_API_KEY = os.getenv('YANDEX_GEOCODER_API_KEY', '')
YANDEX_GEO_SUGGEST_API_KEY = os.getenv('YANDEX_GEO_SUGGEST_API_KEY', '')

# WhiteNoise settings
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_DOMAIN = None

THUMBNAIL_WIDTH = 800
THUMBNAIL_HEIGHT = 600
THUMBNAIL_QUALITY = 85