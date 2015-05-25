from django.conf import settings
from django_hosts import patterns, host

host_patterns = patterns('',
	host(r'api', 'api.urls', name='api'),
	host(r'', settings.ROOT_URLCONF, name='website'),
)
