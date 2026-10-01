import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a .env file (if present) into the environment.
# Copy .env.example to .env and fill in real values — see README.md.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# ✅ SECURITY: read from environment instead of hard-coding.
# Set these in a .env file or your host's environment settings — see README.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-me')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# A device with no reading in this many seconds is shown as DISCONNECTED on the dashboard.
DEVICE_OFFLINE_SECONDS = int(os.environ.get('DEVICE_OFFLINE_SECONDS', '30'))

# Exposed to templates so the frontend polling interval is configurable without a code change.
FRONTEND_POLL_INTERVAL_MS = int(os.environ.get('FRONTEND_POLL_INTERVAL_MS', '3000'))


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',   # ✅ IMPORTANT
    'monitoring',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # ✅ KEEP THIS
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'healthcare.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # ✅ GLOBAL TEMPLATES
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'monitoring.context_processors.frontend_config',
            ],
        },
    },
]


WSGI_APPLICATION = 'healthcare.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'   # ✅ INDIA TIME

USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]


CSRF_TRUSTED_ORIGINS = os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000'
).split(',')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'