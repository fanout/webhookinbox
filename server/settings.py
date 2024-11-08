"""
Django settings for server project.

Generated by 'django-admin startproject' using Django 1.11.20.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'secret')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.environ.get('DJANGO_DEBUG', '1') == '1')

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_hosts',
    'api',
    'website',
]

MIDDLEWARE = [
    'django_hosts.middleware.HostsRequestMiddleware',
    'django_grip.GripMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'api.middleware.OptionsMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_hosts.middleware.HostsResponseMiddleware',
]

ROOT_HOSTCONF = 'server.hosts'
ROOT_URLCONF = 'server.urls'

DEFAULT_HOST = 'website'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'server.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'website': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}

REDIS_HOST = os.environ.get('REDIS_HOST')
if 'REDIS_PORT' in os.environ:
    REDIS_PORT = int(os.environ['REDIS_PORT'])
if 'REDIS_DB' in os.environ:
    REDIS_DB = int(os.environ['REDIS_DB'])

from gripcontrol import parse_grip_uri

GRIP_PROXY_REQUIRED = True
GRIP_URL = os.environ.get('GRIP_URL')

WHINBOX_API_BASE = os.environ.get('WHINBOX_API_BASE')
WHINBOX_REDIS_PREFIX = os.environ.get('WHINBOX_REDIS_PREFIX')
WHINBOX_GRIP_PREFIX = os.environ.get('WHINBOX_GRIP_PREFIX')
WHINBOX_PUBLISH_BLOCKING = (os.environ.get('WHINBOX_PUBLISH_BLOCKING') == '1')
if 'WHINBOX_ITEM_MAX' in os.environ:
    WHINBOX_ITEM_MAX = int(os.environ['WHINBOX_ITEM_MAX'])
if 'WHINBOX_ITEM_BURST_TIME' in os.environ:
    WHINBOX_ITEM_BURST_TIME = int(os.environ['WHINBOX_ITEM_BURST_TIME'])
if 'WHINBOX_ITEM_BURST_MAX' in os.environ:
    WHINBOX_ITEM_BURST_MAX = int(os.environ['WHINBOX_ITEM_BURST_MAX'])
WHINBOX_ORIG_HEADERS = (os.environ.get('WHINBOX_ORIG_HEADERS', '0') == '1')

GA_ID = os.environ.get('GA_ID')
