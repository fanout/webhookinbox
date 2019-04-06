from django.conf import settings
from gripcontrol import HttpResponseFormat
from django_grip import publish
import redis_ops

def _setting(name, default):
	v = getattr(settings, name, None)
	if v is None:
		return default
	return v

db = redis_ops.RedisOps()
grip_prefix = _setting('WHINBOX_GRIP_PREFIX', 'wi-')

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
		publish(grip_prefix + 'wait-%s-%s' % (r[0], r[1]), HttpResponseFormat(code=503, headers=headers, body=body), id='1', prev_id='0')
	return len(reqs)
