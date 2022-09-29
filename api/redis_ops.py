from datetime import datetime
import calendar
import random
import string
import json
import threading
import redis
from django.conf import settings

def _setting(name, default):
	v = getattr(settings, name, None)
	if v is None:
		return default
	return v

class InvalidId(Exception):
	pass

class ObjectExists(Exception):
	pass

class ObjectDoesNotExist(Exception):
	pass

class RedisOps(object):
	def __init__(self):
		self.host = _setting('REDIS_HOST', 'localhost')
		self.port = _setting('REDIS_PORT', 6379)
		self.db = _setting('REDIS_DB', 0)
		self.prefix = _setting('WHINBOX_REDIS_PREFIX', 'wi-')
		self.item_max = _setting('WHINBOX_ITEM_MAX', 100)
		self.item_burst_time = _setting('WHINBOX_ITEM_BURST_TIME', 120)
		self.item_burst_max = _setting('WHINBOX_ITEM_BURST_MAX', 1200)
		self.lock = threading.Lock()
		self.redis = None

	def _get_redis(self):
		self.lock.acquire()
		if not self.redis:
			self.redis = redis.Redis(host=self.host, port=self.port, db=self.db)
		self.lock.release()
		return self.redis

	@staticmethod
	def _gen_id():
		return ''.join(random.choice(string.ascii_letters + string.digits) for n in range(8))

	@staticmethod
	def _validate_id(id):
		for c in id:
			if c not in string.ascii_letters and c not in string.digits and c not in '_-@':
				raise InvalidId('id contains invalid character: %s' % c)

	@staticmethod
	def _timestamp_utcnow():
		return calendar.timegm(datetime.utcnow().utctimetuple())

	# if id=None, then a random id will be used
	# return the id used
	def inbox_create(self, id, ttl, response_mode):
		if id is not None:
			RedisOps._validate_id(id)
		assert(isinstance(ttl, int))
		r = self._get_redis()
		val = dict()
		val['ttl'] = ttl
		val['response_mode'] = response_mode
		set_key = self.prefix + 'inbox'
		exp_key = self.prefix + 'inbox-exp'
		now = RedisOps._timestamp_utcnow()
		while True:
			with r.pipeline() as pipe:
				try:
					if id is not None:
						try_id = id
					else:
						try_id = RedisOps._gen_id()
					key = self.prefix + 'inbox-' + try_id
					pipe.watch(key)
					pipe.watch(exp_key)
					if pipe.exists(key):
						if id is not None:
							raise ObjectExists()
						else:
							# try another random value
							continue
					exp_time = now + ttl
					pipe.multi()
					pipe.set(key, json.dumps(val))
					pipe.sadd(set_key, try_id)
					pipe.zadd(exp_key, try_id, exp_time)
					pipe.execute()
					return try_id
				except redis.WatchError:
					continue

	def inbox_delete(self, id):
		RedisOps._validate_id(id)
		r = self._get_redis()
		key = self.prefix + 'inbox-' + id
		set_key = self.prefix + 'inbox'
		exp_key = self.prefix + 'inbox-exp'
		items_key = self.prefix + 'inbox-items-' + id
		items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(key)
					if not pipe.exists(key):
						raise ObjectDoesNotExist('No such inbox: %s' + id)
					pipe.multi()
					pipe.delete(key)
					pipe.srem(set_key, id)
					pipe.zrem(exp_key, id)
					pipe.delete(items_key)
					pipe.delete(items_baseindex_key)
					pipe.execute()
					break
				except redis.WatchError:
					continue

	def inbox_get(self, id):
		RedisOps._validate_id(id)
		r = self._get_redis()
		key = self.prefix + 'inbox-' + id
		val_json = r.get(key)
		if val_json is None:
			raise ObjectDoesNotExist('No such inbox: %s' + id)
		return json.loads(val_json)

	def inbox_refresh(self, id, newttl=None):
		assert(not newttl or isinstance(newttl, int))
		RedisOps._validate_id(id)
		r = self._get_redis()
		key = self.prefix + 'inbox-' + id
		exp_key = self.prefix + 'inbox-exp'
		now = RedisOps._timestamp_utcnow()
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
					exp_time = now + val['ttl']
					pipe.multi()
					pipe.set(key, json.dumps(val))
					pipe.zadd(exp_key, id, exp_time)
					pipe.execute()
					break
				except redis.WatchError:
					continue

	def inbox_next_expiration(self):
		r = self._get_redis()
		exp_key = self.prefix + 'inbox-exp'
		items = r.zrange(exp_key, 0, 0, withscores=True)
		if len(items) > 0:
			return int(items[0][1])
		else:
			return None

	def inbox_take_expired(self):
		out = list()
		r = self._get_redis()
		set_key = self.prefix + 'inbox'
		exp_key = self.prefix + 'inbox-exp'
		now = RedisOps._timestamp_utcnow()
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

					key = self.prefix + 'inbox-' + id
					items_key = self.prefix + 'inbox-items-' + id
					items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id

					val = json.loads(pipe.get(key))

					pipe.multi()
					pipe.delete(key)
					pipe.srem(set_key, id)
					pipe.zrem(exp_key, id)
					pipe.delete(items_key)
					pipe.delete(items_baseindex_key)
					pipe.execute()

					val['id'] = id
					out.append(val)
					# note: don't break on success
				except redis.WatchError:
					continue
		return out

	# return ids of all inboxes
	def inbox_get_all(self):
		r = self._get_redis()
		set_key = self.prefix + 'inbox'
		return set(r.smembers(set_key))

	# return (item id, prev_id, created)
	def inbox_append_item(self, id, item):
		RedisOps._validate_id(id)
		r = self._get_redis()
		key = self.prefix + 'inbox-' + id
		items_key = self.prefix + 'inbox-items-' + id
		items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(key)
					pipe.watch(items_key)
					pipe.watch(items_baseindex_key)
					if not pipe.exists(key):
						raise ObjectDoesNotExist('No such inbox: %s' + id)
					end_pos = pipe.llen(items_key)
					baseindex = pipe.get(items_baseindex_key)
					if baseindex is not None:
						baseindex = int(baseindex)
					else:
						baseindex = 0
					item['created'] = RedisOps._timestamp_utcnow()
					pipe.multi()
					pipe.rpush(items_key, json.dumps(item))
					pipe.execute()
					prev_pos = baseindex + end_pos - 1
					if prev_pos != -1:
						return (str(baseindex + end_pos), str(prev_pos), item['created'])
					else:
						return (str(baseindex + end_pos), '', item['created'])
				except redis.WatchError:
					continue

	# return (list, last_id)
	def inbox_get_items_after(self, id, item_id, item_max):
		RedisOps._validate_id(id)
		assert(not item_max or item_max > 0)
		r = self._get_redis()
		if item_id is not None and len(item_id) > 0:
			item_pos = int(item_id) + 1
		else:
			item_pos = -1
		key = self.prefix + 'inbox-' + id
		items_key = self.prefix + 'inbox-items-' + id
		items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(key)
					pipe.watch(items_key)
					pipe.watch(items_baseindex_key)
					if not pipe.exists(key):
						raise ObjectDoesNotExist('No such inbox: %s' + id)
					count = pipe.llen(items_key)
					if count == 0:
						return (list(), '')
					baseindex = pipe.get(items_baseindex_key)
					if baseindex is not None:
						baseindex = int(baseindex)
					else:
						baseindex = 0
					if item_pos != -1:
						start_pos = item_pos - baseindex
					else:
						start_pos = 0
					if item_max:
						end_pos = start_pos + item_max - 1
						if end_pos > count - 1:
							end_pos = count - 1
					else:
						end_pos = count - 1
					if start_pos > end_pos:
						return (list(), str(baseindex + end_pos))
					pipe.multi()
					pipe.lrange(items_key, start_pos, end_pos)
					ret = pipe.execute()
					items_json = ret[0]
					items = list()
					for n, i in enumerate(items_json):
						item = json.loads(i)
						item['id'] = str(baseindex + start_pos + n)
						items.append(item)
					return (items, str(baseindex + end_pos))
				except redis.WatchError:
					continue

	# return (list, last_id, eof)
	def inbox_get_items_before(self, id, item_id, item_max):
		RedisOps._validate_id(id)
		assert(not item_max or item_max > 0)
		r = self._get_redis()
		if item_id is not None and len(item_id) > 0:
			item_pos = int(item_id) - 1
			if item_pos < 0:
				return (list(), '', True)
		else:
			item_pos = -1
		key = self.prefix + 'inbox-' + id
		items_key = self.prefix + 'inbox-items-' + id
		items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(key)
					pipe.watch(items_key)
					pipe.watch(items_baseindex_key)
					if not pipe.exists(key):
						raise ObjectDoesNotExist('No such inbox: %s' + id)
					count = pipe.llen(items_key)
					if count == 0:
						return (list(), '', True)
					baseindex = pipe.get(items_baseindex_key)
					if baseindex is not None:
						baseindex = int(baseindex)
					else:
						baseindex = 0
					if item_pos != -1:
						end_pos = item_pos - baseindex
					else:
						end_pos = count - 1
					if item_max:
						start_pos = end_pos - (item_max - 1)
						if start_pos < 0:
							start_pos = 0
					else:
						start_pos = 0
					if start_pos > end_pos:
						return (list(), str(baseindex + start_pos), start_pos == 0)
					pipe.multi()
					pipe.lrange(items_key, start_pos, end_pos)
					ret = pipe.execute()
					items_json = ret[0]
					items = list()
					for n, i in enumerate(items_json):
						item = json.loads(i)
						item['id'] = str(baseindex + start_pos + n)
						items.insert(0, item)
					return (items, str(baseindex + start_pos), start_pos == 0)
				except redis.WatchError:
					continue

	def inbox_get_newest_id(self, id):
		RedisOps._validate_id(id)
		r = self._get_redis()
		key = self.prefix + 'inbox-' + id
		items_key = self.prefix + 'inbox-items-' + id
		items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(key)
					pipe.watch(items_key)
					pipe.watch(items_baseindex_key)
					if not pipe.exists(key):
						raise ObjectDoesNotExist('No such inbox: %s' + id)
					count = pipe.llen(items_key)
					if count == 0:
						return ''
					baseindex = pipe.get(items_baseindex_key)
					if baseindex is not None:
						baseindex = int(baseindex)
					else:
						baseindex = 0
					last_pos = count - 1
					pipe.multi()
					pipe.execute()
					return str(baseindex + last_pos)
				except redis.WatchError:
					continue

	def inbox_clear_expired_items(self, id):
		RedisOps._validate_id(id)
		r = self._get_redis()
		items_key = self.prefix + 'inbox-items-' + id
		items_baseindex_key = self.prefix + 'inbox-items-baseindex-' + id
		now = RedisOps._timestamp_utcnow()
		total = 0
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(items_key)
					pipe.watch(items_baseindex_key)

					items = pipe.lrange(items_key, 0, 0)
					if not items:
						break

					item = json.loads(items[0])

					count = pipe.llen(items_key)

					item_pos = 0
					item_time = item['created']

					expire = False
					if item_time > now - self.item_burst_time:
						if item_pos < count - self.item_burst_max:
							expire = True
					else:
						if item_pos < count - self.item_max:
							expire = True

					if not expire:
						break

					pipe.multi()
					pipe.lpop(items_key)
					pipe.incr(items_baseindex_key)
					pipe.execute()

					total += 1

					# note: don't break on success
				except redis.WatchError:
					continue
		return total

	def request_add_pending(self, inbox_id, item_id):
		r = self._get_redis()
		req_id = inbox_id + '-' + item_id
		req_key = self.prefix + 'req-item-' + req_id
		req_exp_key = self.prefix + 'req-exp'
		now = RedisOps._timestamp_utcnow()
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(req_key)
					pipe.watch(req_exp_key)
					if pipe.exists(req_key):
						raise ObjectExists()
					exp_time = now + 20
					pipe.multi()
					pipe.set(req_key, json.dumps([inbox_id, item_id]))
					pipe.zadd(req_exp_key, req_id, exp_time)
					pipe.execute()
					break
				except redis.WatchError:
					continue

	def request_remove_pending(self, inbox_id, item_id):
		r = self._get_redis()
		req_id = inbox_id + '-' + item_id
		req_key = self.prefix + 'req-item-' + req_id
		req_exp_key = self.prefix + 'req-exp'
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(req_key)
					pipe.watch(req_exp_key)
					if not pipe.exists(req_key):
						raise ObjectDoesNotExist()
					pipe.multi()
					pipe.delete(req_key)
					pipe.zrem(req_exp_key, req_id)
					pipe.execute()
					break
				except redis.WatchError:
					continue

	def request_is_pending(self, inbox_id, item_id):
		r = self._get_redis()
		req_id = inbox_id + '-' + item_id
		req_key = self.prefix + 'req-item-' + req_id
		return r.exists(req_key)

	# return list((inbox_id, item_id))
	def request_take_expired(self):
		out = list()
		r = self._get_redis()
		req_exp_key = self.prefix + 'req-exp'
		now = RedisOps._timestamp_utcnow()
		while True:
			with r.pipeline() as pipe:
				try:
					pipe.watch(req_exp_key)

					items = pipe.zrange(req_exp_key, 0, 0, withscores=True)
					if len(items) == 0:
						break
					if int(items[0][1]) > now:
						break
					req_id = items[0][0]

					req_key = self.prefix + 'req-item-' + req_id
					pipe.watch(req_key)
					val_raw = pipe.get(req_key)
					if not val_raw:
						continue

					val = json.loads(val_raw)
					inbox_id = val[0]
					item_id = val[1]

					pipe.multi()
					pipe.delete(req_key)
					pipe.zrem(req_exp_key, req_id)
					pipe.execute()

					out.append((inbox_id, item_id))
					# note: don't break on success
				except redis.WatchError:
					continue
		return out
