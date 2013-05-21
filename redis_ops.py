from datetime import datetime
import calendar
import random
import string
import json
import threading
import redis

g_lock = threading.Lock()
g_prefix = ''
g_redis_host = 'localhost'
g_redis_port = 6379
g_redis = None

class ObjectDoesNotExist(Exception):
	pass

class InvalidId(Exception):
	pass

def set_config(prefix, host, port):
	global g_prefix
	global g_redis_host
	global g_redis_port
	g_lock.acquire()
	g_prefix = prefix
	g_redis_host = host
	g_redis_port = port
	g_lock.release()

def get_redis():
	global g_redis
	g_lock.acquire()
	if not g_redis:
		g_redis = redis.Redis(host=g_redis_host, port=g_redis_port)
	g_lock.release()
	return g_redis

def gen_id():
	return ''.join(random.choice(string.letters + string.digits) for n in xrange(8))

def validate_id(id):
	for c in id:
		if c not in string.letters and c not in string.digits:
			raise InvalidId('id contains invalid character: %s' % c)

def timestamp_utcnow():
	return calendar.timegm(datetime.utcnow().utctimetuple())

def inbox_create(ttl):
	assert(isinstance(ttl, int))
	r = get_redis()
	val = dict()
	val['ttl'] = ttl
	now = timestamp_utcnow()
	while True:
		with r.pipeline() as pipe:
			try:
				id = gen_id()
				key = g_prefix + 'inbox-' + id
				exp_key = g_prefix + 'exp'
				pipe.watch(key)
				pipe.watch(exp_key)
				if pipe.exists(key):
					# try another random value
					continue
				exp_time = now + (ttl * 60)
				pipe.multi()
				pipe.set(key, json.dumps(val))
				pipe.zadd(exp_key, id, exp_time)
				pipe.execute()
				return id
			except redis.WatchError:
				continue

def inbox_delete(id):
	validate_id(id)
	r = get_redis()
	key = g_prefix + 'inbox-' + id
	exp_key = g_prefix + 'exp'
	items_key = g_prefix + 'inbox-items-' + id
	while True:
		with r.pipeline() as pipe:
			try:
				pipe.watch(key)
				if not pipe.exists(key):
					raise ObjectDoesNotExist('No such inbox: %s' + id)
				pipe.multi()
				pipe.delete(key)
				pipe.zrem(exp_key, id)
				pipe.delete(items_key)
				pipe.execute()
				break
			except redis.WatchError:
				continue

def inbox_get(id):
	validate_id(id)
	r = get_redis()
	key = g_prefix + 'inbox-' + id
	val_json = r.get(key)
	if val_json is None:
		raise ObjectDoesNotExist('No such inbox: %s' + id)
	return json.loads(val_json)

def inbox_refresh(id, newttl=None):
	assert(not newttl or isinstance(newttl, int))
	validate_id(id)
	r = get_redis()
	key = g_prefix + 'inbox-' + id
	exp_key = g_prefix + 'exp'
	now = timestamp_utcnow()
	while True:
		with r.pipeline() as pipe:
			try:
				pipe.watch(key)
				pipe.watch(exp_key)
				val_json = pipe.get(key)
				if val_json is None:
					raise ObjectDoesNotExist('No such inbox: %s' + id)
				val = json.loads(val_json)
				if newttl is not None:
					val['ttl'] = newttl
				exp_time = now + (val['ttl'] * 60)
				pipe.multi()
				pipe.set(key, json.dumps(val))
				pipe.zadd(exp_key, id, exp_time)
				pipe.execute()
				break
			except redis.WatchError:
				continue

def inbox_next_expiration():
	r = get_redis()
	exp_key = g_prefix + 'exp'
	items = r.zrange(exp_key, 0, 0, withscores=True)
	if len(items) > 0:
		return int(items[0][1])
	else:
		return None

def inbox_take_expired():
	out = list()
	r = get_redis()
	exp_key = g_prefix + 'exp'
	now = timestamp_utcnow()
	while True:
		with r.pipeline() as pipe:
			try:
				pipe.watch(exp_key)

				items = pipe.zrange(exp_key, 0, 0, withscores=True)
				if len(items) == 0:
					break
				if int(items[0][1]) > now:
					break
				id = items[0][0]
				key = g_prefix + 'inbox-' + id
				val = json.loads(pipe.get(key))

				pipe.multi()
				pipe.zrem(exp_key, id)
				pipe.delete(key)
				pipe.execute()

				val['id'] = id
				out.append(val)
				# note: don't break on success
			except redis.WatchError:
				continue
	return out

# return (item id, prev_id)
def inbox_append_item(id, item):
	validate_id(id)
	r = get_redis()
	key = g_prefix + 'inbox-' + id
	items_key = g_prefix + 'inbox-items-' + id
	while True:
		with r.pipeline() as pipe:
			try:
				pipe.watch(key)
				pipe.watch(items_key)
				if not pipe.exists(key):
					raise ObjectDoesNotExist('No such inbox: %s' + id)
				end_pos = pipe.llen(items_key)
				pipe.multi()
				pipe.rpush(items_key, json.dumps(item))
				pipe.execute()
				prev_pos = end_pos - 1
				if prev_pos != -1:
					return (str(end_pos), str(prev_pos))
				else:
					return (str(end_pos), '')
			except redis.WatchError:
				continue

# return (list, last_id)
def inbox_get_items_after(id, item_id):
	validate_id(id)
	r = get_redis()
	if len(item_id) > 0:
		item_pos = int(item_id)
	else:
		item_pos = -1
	key = g_prefix + 'inbox-' + id
	items_key = g_prefix + 'inbox-items-' + id
	while True:
		with r.pipeline() as pipe:
			try:
				pipe.watch(key)
				pipe.watch(items_key)
				if not pipe.exists(key):
					raise ObjectDoesNotExist('No such inbox: %s' + id)
				count = pipe.llen(items_key)
				if count == 0:
					return (list(), '')
				last_pos = count - 1
				if item_pos >= last_pos:
					return (list(), str(last_pos))
				pipe.multi()
				pipe.lrange(items_key, item_pos + 1, last_pos)
				ret = pipe.execute()
				items_json = ret[0]
				items = list()
				for i in items_json:
					items.append(json.loads(i))
				return (items, str(last_pos))
			except redis.WatchError:
				continue

def inbox_get_last_id(id):
	validate_id(id)
	r = get_redis()
	key = g_prefix + 'inbox-' + id
	items_key = g_prefix + 'inbox-items-' + id
	while True:
		with r.pipeline() as pipe:
			try:
				pipe.watch(key)
				pipe.watch(items_key)
				if not pipe.exists(key):
					raise ObjectDoesNotExist('No such inbox: %s' + id)
				count = pipe.llen(items_key)
				if count == 0:
					return ''
				last_pos = count - 1
				pipe.multi()
				pipe.execute()
				return str(last_pos)
			except redis.WatchError:
				continue
