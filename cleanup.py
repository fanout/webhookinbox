from django.conf import settings
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

if hasattr(settings, 'WHINBOX_ITEM_MAX'):
	db.item_max = settings.WHINBOX_ITEM_MAX

if hasattr(settings, 'WHINBOX_ITEM_BURST_TIME'):
	db.item_burst_time = settings.WHINBOX_ITEM_BURST_TIME

if hasattr(settings, 'WHINBOX_ITEM_BURST_MAX'):
	db.item_burst_max = settings.WHINBOX_ITEM_BURST_MAX

# expire any inboxes
expired = db.inbox_take_expired()

print "expired %d inboxes" % len(expired)

# expire items of remaining inboxes
inboxes = db.inbox_get_all()
count = 0
for inbox in inboxes:
	count += db.inbox_clear_expired_items(inbox)

print "expired %d items in %d active inboxes" % (count, len(inboxes))
