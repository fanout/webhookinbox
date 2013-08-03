import time
from django.conf import settings
import grip
import redis_ops

db = redis_ops.RedisOps()
pub = grip.Publisher()

if hasattr(settings, 'REDIS_HOST'):
	db.host = settings.REDIS_HOST

if hasattr(settings, 'REDIS_PORT'):
	db.port = settings.REDIS_PORT

if hasattr(settings, 'REDIS_DB'):
	db.db = settings.REDIS_DB

if hasattr(settings, 'GRIP_PROXIES'):
	grip_proxies = settings.GRIP_PROXIES
else:
	grip_proxies = list()

if hasattr(settings, 'WHINBOX_REDIS_PREFIX'):
	db.prefix = settings.WHINBOX_REDIS_PREFIX
else:
	db.prefix = 'wi-'

if hasattr(settings, 'WHINBOX_GRIP_PREFIX'):
	grip_prefix = settings.WHINBOX_GRIP_PREFIX
else:
	grip_prefix = 'wi-'

if hasattr(settings, 'WHINBOX_ITEM_MAX'):
	db.item_max = settings.WHINBOX_ITEM_MAX

if hasattr(settings, 'WHINBOX_ITEM_BURST_TIME'):
	db.item_burst_time = settings.WHINBOX_ITEM_BURST_TIME

if hasattr(settings, 'WHINBOX_ITEM_BURST_MAX'):
	db.item_burst_max = settings.WHINBOX_ITEM_BURST_MAX

pub.proxies = grip_proxies

def expire_inboxes():
	expired = db.inbox_take_expired()
	print 'expired %d inboxes' % len(expired)

def expire_items():
	inboxes = db.inbox_get_all()
	count = 0
	for inbox in inboxes:
		count += db.inbox_clear_expired_items(inbox)
	print 'expired %d items in %d active inboxes' % (count, len(inboxes))

def expire_requests():
	reqs = db.request_take_expired()
	headers = dict()
	headers['Content-Type'] = 'text/html'
	body = 'Service Unavailable\n'
	for r in reqs:
		pub.publish(grip_prefix + 'wait-' + r[0] + '-' + r[1], None, None, headers, body, code=503)
	print 'expired %d requests' % len(reqs)

expire_inboxes()

# expire items of remaining inboxes
expire_items()

# we expect this program to run once per minute, so to achieve a 10 second
#   interval, we'll do 6 iterations within a single run
for n in range(0, 6):
	if n != 0:
		time.sleep(10)
	expire_requests()
