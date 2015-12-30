"""
Django settings for sppfawards project.

"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'insecure_default_key')

DEBUG = True

TEMPLATE_DEBUG = True


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'serebii',
    'awards',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'serebii.models.UnverifiedUserMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "awards.views.awards_context",
)

ROOT_URLCONF = 'sppfawards.urls'

WSGI_APPLICATION = 'sppfawards.wsgi.application'

AUTH_USER_MODEL = 'serebii.User'

LOGIN_REDIRECT_URL = 'home'

LOGIN_URL = 'login'


# Serebii awards settings

MIN_YEAR = 2008

MAX_YEAR = 2015  # This should be changed every year

YEAR = int(os.environ.get('YEAR', MAX_YEAR))

def parse_environ_date(key):
    environ_date = os.environ.get(key, None)
    return datetime.strptime(environ_date, '%Y-%m-%d') if environ_date is not None else None

NOMINATION_START = parse_environ_date('NOMINATION_START')
VOTING_START = parse_environ_date('VOTING_START')
VOTING_END = parse_environ_date('VOTING_END')

DISCUSSION_THREAD = os.environ.get('DISCUSSION_THREAD', '')
NOMINATION_THREAD = os.environ.get('NOMINATION_THREAD', '')
VOTING_THREAD = os.environ.get('VOTING_THREAD', '')
RESULTS_THREAD = os.environ.get('RESULTS_THREAD', '')

MAX_FIC_NOMINATIONS = int(os.environ.get('MAX_FIC_NOMINATIONS', 5))
MAX_PERSON_NOMINATIONS = int(os.environ.get('MAX_PERSON_NOMINATIONS', 6))
MIN_DIFFERENT_NOMINATIONS = int(os.environ.get('MIN_DIFFERENT_NOMINATIONS', 4))

SEREBII_USER_ID = os.environ.get('SEREBII_USER_ID', '')
SEREBII_USER_PWHASH = os.environ.get('SEREBII_USER_PWHASH', '')


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Parse database configuration from $DATABASE_URL
import dj_database_url
dbconfig  = dj_database_url.config()
if dbconfig:
    DATABASES['default'] =  dbconfig

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static asset configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

environ_debug = os.environ.get('DJANGO_DEBUG')
if environ_debug is not None:
    DEBUG = bool(int(environ_debug))
    TEMPLATE_DEBUG = DEBUG

# Import local settings overrides if they exist
try:
    from sppfawards.local_settings import *
except ImportError as e:
    pass