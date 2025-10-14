import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

import os
DEBUG = os.getenv('DEBUG', '0') == '1'

load_dotenv()
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dqgwzhywm',
    'API_KEY': '164662831511784',
    'API_SECRET': 'aGZYpvwhUCuFiAaYAgXeOIr-FIk',
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
    cloud_name= CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key= CLOUDINARY_STORAGE['API_KEY'],
    api_secret= CLOUDINARY_STORAGE['API_SECRET'],
    secure=True
)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))


SECRET_KEY = 'xs-n-y_rwpn!5$25=lm@c4lyi%(fk4j@2t-fx6v1dfb$1i8%-3'



handler500 = 'accounts.views.server_error'
ALLOWED_HOSTS = [
    "*",  # Разрешает все хосты (уже есть)
    "localhost",
    "127.0.0.1",
    "192.168.1.98",  # Ваш IPвфы (уже есть)
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://192.168.1.98:8000',  # Ваш IP (уже есть)
]

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
    'django.contrib.gis',
    'django_filters',
    'widget_tweaks',
    'channels',
    'corsheaders',
    'django.contrib.humanize',





]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.ActivityLoggerMiddleware',
    'accounts.middleware.ProfileCompletionMiddleware',
    'corsheaders.middleware.CorsMiddleware',

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

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'db',
        'PORT': '5432',
    }
}

# Валидация паролей
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
#DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Настройки Whitenoise для статических файлов
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

AUTH_USER_MODEL = 'accounts.User'


LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'


#AWS_S3_SIGNATURE_VERSION = 's3v4'
#AWS_DEFAULT_ACL = 'public-read'
#AWS_QUERYSTRING_AUTH = False
#AWS_S3_OBJECT_PARAMETERS = {
    #'CacheControl': 'max-age=86400',
#}

#if DEBUG:
    #DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    # Убедитесь, что MEDIA_ROOT и MEDIA_URL настроены
   # MEDIA_URL = '/media/'
    #MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
#else:
    #DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # Настройки S3 (оставьте ваши текущие AWS-ключи и endpoint)
    #AWS_ACCESS_KEY_ID = '95bf86962b9e4d1d94958be095e5d901'
   # AWS_SECRET_ACCESS_KEY = 'fpwzZRsVN2jkAkUD9hvYQ5'
    #AWS_STORAGE_BUCKET_NAME = 'money'
   # AWS_S3_ENDPOINT_URL = 'https://hb.ru-1.storage.cloud.mail.ru'
   # AWS_S3_REGION_NAME = 'ru-1'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = 'goldinpav@yandex.ru'
EMAIL_HOST_PASSWORD = 'mglkpkdkfapyubfa'
DEFAULT_FROM_EMAIL = 'WinWinDeal <goldinpav@yandex.ru>'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
YOOMONEY_ACCOUNT_ID = '1105130'
YOOMONEY_SECRET_KEY = 'test_evMMyWGLIawYaOMUELuBxzSO5XJbnaDcrJeulp2lX8w'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True


class OwnerAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(creator=request.user)

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

if os.path.exists('package.json'):
    with open('package.json', 'w') as f:
        f.write('{"private": true, "scripts": {}}')

# Проверка статических файлов
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
# Добавьте в settings.py
# Добавляем в settings.py
YANDEX_MAPS_API_KEY = '3585e6f5-6323-4098-8a4d-b279da5b0c4f'  # Основной ключ для JavaScript API
YANDEX_GEOCODER_API_KEY = '3585e6f5-6323-4098-8a4d-b279da5b0c4f'  # Для геокодирования

YANDEX_GEO_SUGGEST_API_KEY = '7979f3d5-7f35-4fd8-893c-e5f1ecaeb3a4'  # Для геосаджеста
# Для принудительного обслуживания статики через WhiteNoise
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_DOMAIN = None

THUMBNAIL_WIDTH = 800
THUMBNAIL_HEIGHT = 600
THUMBNAIL_QUALITY = 85