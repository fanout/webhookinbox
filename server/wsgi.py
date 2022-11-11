"""
WSGI config for server project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os

import dotenv
from django.core.wsgi import get_wsgi_application

dotenv.read_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

from django.conf import settings

if not settings.DEBUG:
	from whitenoise import DjangoWhiteNoise
	application = DjangoWhiteNoise(get_wsgi_application())
else:
	from dj_static import Cling
	application = Cling(get_wsgi_application())
