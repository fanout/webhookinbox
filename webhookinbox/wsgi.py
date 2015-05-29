"""
WSGI config for webhookinbox project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webhookinbox.settings")

vars = (
	'DJANGO_SECRET_KEY',
	'DJANGO_DEBUG',
	'REDIS_HOST',
	'REDIS_PORT',
	'REDIS_DB',
	'GRIP_URL',
	'WHINBOX_API_BASE',
	'WHINBOX_REDIS_PREFIX',
	'WHINBOX_GRIP_PREFIX',
	'WHINBOX_ITEM_MAX',
	'WHINBOX_ITEM_BURST_TIME',
	'WHINBOX_ITEM_BURST_MAX',
	'WHINBOX_ORIG_HEADERS',
)

from django.core.wsgi import get_wsgi_application
from django.conf import settings

def application(environ, start_response):
	for var in vars:
		if var in environ:
			os.environ[var] = environ[var]
	if not settings.DEBUG:
		from whitenoise.django import DjangoWhiteNoise
		return DjangoWhiteNoise(get_wsgi_application())(environ, start_response)
	else:
		from dj_static import Cling
		return Cling(get_wsgi_application())(environ, start_response)
