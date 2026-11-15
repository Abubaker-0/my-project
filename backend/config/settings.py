"""Runtime settings for the Course Tuition Center MIS.

The application database is MySQL (`course_tuition_center_mis`, utf8mb4), which
matches a local XAMPP install. The test runner uses SQLite unless TEST_DB=mysql
so the business-rule suite can run without a database server.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == 'test'

SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'dev-only-tuition-mis-change-this-key-32b',
)
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

if not DEBUG and SECRET_KEY.startswith('dev-only-'):
    raise RuntimeError('Set DJANGO_SECRET_KEY before running with DJANGO_DEBUG=False.')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'apps.common',
    'apps.centers',
    'apps.accounts',
    'apps.courses',
    'apps.classes',
    'apps.enrollments',
    'apps.attendance',
    'apps.finance',
    'apps.reports',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DB_ENGINE = os.getenv('DB_ENGINE', 'mysql').lower()
if RUNNING_TESTS and os.getenv('TEST_DB', 'sqlite') != 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
elif DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'course_tuition_center_mis'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

if RUNNING_TESTS:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kabul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_RENDERER_CLASSES': ('apps.common.renderers.ApiRenderer',),
    'EXCEPTION_HANDLER': 'apps.common.exceptions.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'login': '20/min',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]
CORS_ALLOW_HEADERS = (
    'accept',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
)

SUPER_ADMIN_USERNAME = os.getenv('SUPER_ADMIN_USERNAME', 'superadmin')
SUPER_ADMIN_EMAIL = os.getenv('SUPER_ADMIN_EMAIL', 'superadmin@tuition.local')
SUPER_ADMIN_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD', 'Admin@12345')
SUPER_ADMIN_FIRST_NAME = os.getenv('SUPER_ADMIN_FIRST_NAME', 'System')
SUPER_ADMIN_LAST_NAME = os.getenv('SUPER_ADMIN_LAST_NAME', 'Administrator')
SUPER_ADMIN_PHONE = os.getenv('SUPER_ADMIN_PHONE', '+93700000000')
SUPER_ADMIN_GENDER = os.getenv('SUPER_ADMIN_GENDER', 'male')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'security': {'handlers': ['console'], 'level': 'WARNING'},
        'business': {'handlers': ['console'], 'level': 'INFO'},
    },
}

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = os.getenv('SECURE_SSL', 'False').lower() in ('1', 'true', 'yes')
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
    SECURE_SSL_REDIRECT = SESSION_COOKIE_SECURE
