import time
from django.conf import settings
from gripcontrol import HttpResponseFormat
from django_grip import publish
import redis_ops

db = redis_ops.RedisOps()

if hasattr(settings, 'REDIS_HOST'):
	db.host = settings.REDIS_HOST

if hasattr(settings, 'REDIS_PORT'):
	db.port = settings.REDIS_PORT

if hasattr(settings, 'REDIS_DB'):
	db.db = settings.REDIS_DB

if hasattr(settings, 'WHINBOX_REDIS_PREFIX'):
	db.prefix = settings.WHINBOX_REDIS_PREFIX
else:
	db.prefix = 'wi-'

if hasattr(settings, 'WHINBOX_GRIP_PREFIX'):
	grip_prefix = settings.WHINBOX_GRIP_PREFIX
else:
	grip_prefix = ''

if hasattr(settings, 'WHINBOX_ITEM_MAX'):
	db.item_max = settings.WHINBOX_ITEM_MAX

if hasattr(settings, 'WHINBOX_ITEM_BURST_TIME'):
	db.item_burst_time = settings.WHINBOX_ITEM_BURST_TIME

if hasattr(settings, 'WHINBOX_ITEM_BURST_MAX'):
	db.item_burst_max = settings.WHINBOX_ITEM_BURST_MAX

def expire_inboxes():
	return len(db.inbox_take_expired())

def expire_items():
	inboxes = db.inbox_get_all()
	count = 0
	for inbox in inboxes:
		count += db.inbox_clear_expired_items(inbox)
	return (count, len(inboxes))

def expire_requests():
	reqs = db.request_take_expired()
	headers = dict()
	headers['Content-Type'] = 'text/html'
	body = 'Service Unavailable\n'
	for r in reqs:
		publish(grip_prefix + 'wait-%s-%s' % (r[0], r[1]), HttpResponseFormat(code=503, headers=headers, body=body))
	return len(reqs)
