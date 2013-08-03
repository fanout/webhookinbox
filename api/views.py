from base64 import b64encode, b64decode
import datetime
import copy
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed
import gripcontrol
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

if hasattr(settings, 'WHINBOX_ORIG_HEADERS'):
	orig_headers = True
else:
	orig_headers = False

pub.proxies = grip_proxies

# useful list derived from requestbin
ignore_headers = """
X-Varnish
X-Forwarded-For
X-Heroku-Dynos-In-Use
X-Request-Start
X-Heroku-Queue-Wait-Time
X-Heroku-Queue-Depth
X-Real-Ip
X-Forwarded-Proto
X-Via
X-Forwarded-Port
Grip-Sig
""".split("\n")[1:-1]

def _ignore_header(name):
	name = name.lower()
	for h in ignore_headers:
		if name == h.lower():
			return True
	return False

def _convert_header_name(name):
	out = ''
	word_start = True
	for c in name:
		if c == '_':
			out += '-'
			word_start = True
		elif word_start:
			out += c.upper()
			word_start = False
		else:
			out += c.lower()
	return out

def _req_to_item(req):
	item = dict()
	item['method'] = req.method
	item['path'] = req.path
	query = req.META.get('QUERY_STRING')
	if query:
		item['query'] = query
	raw_headers = list()
	content_length = req.META.get('CONTENT_LENGTH')
	if content_length:
		raw_headers.append(('CONTENT_LENGTH', content_length))
	content_type = req.META.get('CONTENT_TYPE')
	if content_type:
		raw_headers.append(('CONTENT_TYPE', content_type))
	for k, v in req.META.iteritems():
		if k.startswith('HTTP_'):
			raw_headers.append((k[5:], v))
	# undjangoify the header names
	headers = list()
	for h in raw_headers:
		headers.append((_convert_header_name(h[0]), h[1]))
	if orig_headers:
		# if this option is set, then we assume the exact headers are magic prefixed
		tmp = list()
		for h in headers:
			if h[0].lower().startswith('eb9bf0f5-'):
				tmp.append((h[0][9:], h[1]))
		headers = tmp
	else:
		# otherwise, use the blacklist to clean things up
		tmp = list()
		for h in headers:
			if not _ignore_header(h[0]):
				tmp.append(h)
		headers = tmp
	item['headers'] = headers
	if len(req.raw_post_data) > 0:
		try:
			# if the body is valid utf-8, then store as text
			body = req.raw_post_data.decode('utf-8')
			item['body'] = body
		except:
			# else, store as binary
			item['body-bin'] = b64encode(req.raw_post_data)
	forwardedfor = req.META.get('HTTP_X_FORWARDED_FOR')
	if forwardedfor:
		ip_address = forwardedfor.split(',')[0].strip()
	else:
		ip_address = req.META['REMOTE_ADDR']
	item['ip_address'] = ip_address
	return item

def _convert_item(item, responded=False):
	out = copy.deepcopy(item)
	created = datetime.datetime.fromtimestamp(item['created']).isoformat()
	if len(created) > 0 and created[-1] != 'Z':
		created += 'Z'
	out['created'] = created
	if responded:
		out['state'] = 'responded'
	else:
		out['state'] = 'response-pending'
	return out

def root(req):
	return HttpResponseNotFound('Not Found\n')

def create(req):
	if req.method == 'POST':
		host = req.META.get('HTTP_HOST')
		if not host:
			return HttpResponseBadRequest('Bad Request: No \'Host\' header\n')

		inbox_id = req.POST.get('id')

		ttl = req.POST.get('ttl')
		if ttl is not None:
			ttl = int(ttl)
		if ttl is None:
			ttl = 3600

		response_mode = req.POST.get('response_mode')
		if not response_mode:
			response_mode = 'auto'
		if response_mode not in ('auto', 'wait-verify', 'wait'):
			return HttpResponseBadRequest('Bad Request: response_mode must be "auto", "auto-verify", or "wait"\n')

		try:
			inbox_id = db.inbox_create(inbox_id, ttl, response_mode)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		out = dict()
		out['id'] = inbox_id
		out['base_url'] = 'http://' + host + '/i/' + inbox_id + '/'
		out['ttl'] = ttl
		out['response_mode'] = response_mode
		return HttpResponse(json.dumps(out) + '\n', content_type='application/json')
	else:
		return HttpResponseNotAllowed(['POST'])

def inbox(req, inbox_id):
	if req.method == 'GET':
		host = req.META.get('HTTP_HOST')
		if not host:
			return HttpResponseBadRequest('Bad Request: No \'Host\' header\n')

		try:
			inbox = db.inbox_get(inbox_id)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		out = dict()
		out['id'] = inbox_id
		out['base_url'] = 'http://' + host + '/i/' + inbox_id + '/'
		out['ttl'] = inbox['ttl']
		response_mode = inbox.get('response_mode')
		if not response_mode:
			response_mode = 'auto'
		out['response_mode'] = response_mode
		return HttpResponse(json.dumps(out) + '\n', content_type='application/json')
	elif req.method == 'DELETE':
		try:
			db.inbox_delete(inbox_id)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		# we'll push a 404 to any long polls because we're that cool
		hr_headers = dict()
		hr_headers['Content-Type'] = 'text/html'
		hr_body = 'Not Found\n'

		pub.publish(grip_prefix + 'inbox-' + inbox_id, None, None, hr_headers, hr_body, code=404)

		return HttpResponse('Deleted\n')
	else:
		return HttpResponseNotAllowed(['GET', 'DELETE'])

def refresh(req, inbox_id):
	if req.method == 'POST':
		ttl = req.POST.get('ttl')
		if ttl is not None:
			ttl = int(ttl)

		try:
			db.inbox_refresh(inbox_id, ttl)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		return HttpResponse('Refreshed\n')
	else:
		return HttpResponseNotAllowed(['POST'])

def respond(req, inbox_id, item_id):
	if req.method == 'POST':
		try:
			content = json.loads(req.raw_post_data)
		except:
			return HttpResponseBadRequest('Bad Request: Body must be valid JSON\n')

		try:
			code = content.get('code')
			if code is not None:
				code = int(code)
			else:
				code = 200

			reason = content.get('reason')
			headers = content.get('headers')

			if 'body-bin' in content:
				body = b64decode(content['body-bin'])
			elif 'body' in content:
				body = content['body']
			else:
				body = ''
		except:
			return HttpResponseBadRequest('Bad Request: Bad format of response\n')

		try:
			db.request_remove_pending(inbox_id, item_id)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		pub.publish(grip_prefix + 'wait-' + inbox_id + '-' + item_id, None, None, headers, body, None, code, reason)

		return HttpResponse('Ok\n')
	else:
		return HttpResponseNotAllowed(['POST'])

def hit(req, inbox_id):
	try:
		inbox = db.inbox_get(inbox_id)
	except redis_ops.InvalidId:
		return HttpResponseBadRequest('Bad Request: Invalid id\n')
	except redis_ops.ObjectDoesNotExist:
		return HttpResponseNotFound('Not Found\n')
	except:
		return HttpResponse('Service Unavailable\n', status=503)

	response_mode = inbox.get('response_mode')
	if not response_mode:
		response_mode = 'auto'

	# pubsubhubbub verify request?
	hub_challenge = req.GET.get('hub.challenge')

	if response_mode == 'wait' or (response_mode == 'wait-verify' and hub_challenge):
		respond_now = False
	else:
		respond_now = True

	item = _req_to_item(req)
	if hub_challenge:
		item['type'] = 'hub-verify'
	else:
		item['type'] = 'normal'

	try:
		item_id, prev_id, item_created = db.inbox_append_item(inbox_id, item)
		db.inbox_clear_expired_items(inbox_id)
	except redis_ops.InvalidId:
		return HttpResponseBadRequest('Bad Request: Invalid id\n')
	except redis_ops.ObjectDoesNotExist:
		return HttpResponseNotFound('Not Found\n')
	except:
		return HttpResponse('Service Unavailable\n', status=503)

	item['id'] = item_id
	item['created'] = item_created

	item = _convert_item(item, respond_now)

	hr_headers = dict()
	hr_headers['Content-Type'] = 'application/json'
	hr = dict()
	hr['last_cursor'] = item_id
	hr['items'] = [item]
	hr_body = json.dumps(hr) + '\n'
	hs_body = json.dumps(item) + '\n'

	pub.publish(grip_prefix + 'inbox-' + inbox_id, item_id, prev_id, hr_headers, hr_body, hs_body)

	if respond_now:
		if hub_challenge:
			return HttpResponse(hub_challenge)
		else:
			return HttpResponse('Ok\n')
	else:
		if not grip.is_proxied(req, grip_proxies):
			return HttpResponse('Not Implemented\n', status=501)

		# wait for the user to respond
		db.request_add_pending(inbox_id, item_id)
		channel = gripcontrol.Channel(grip_prefix + 'wait-' + inbox_id + '-' + item_id)
		theaders = dict()
		theaders['Content-Type'] = 'text/html'
		tbody = 'Service Unavailable\n'
		tresponse = gripcontrol.Response(code=503, headers=theaders, body=tbody)
		instruct = gripcontrol.create_hold_response(channel, tresponse)
		return HttpResponse(instruct, content_type='application/grip-instruct')

def items(req, inbox_id):
	if req.method == 'GET':
		try:
			db.inbox_refresh(inbox_id)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		order = req.GET.get('order')
		if order and order not in ('created', '-created'):
			return HttpResponseBadRequest('Bad Request: Invalid order value\n')

		if not order:
			order = 'created'

		imax = req.GET.get('max')
		if imax:
			try:
				imax = int(imax)
				if imax < 1:
					raise ValueError('max too small')
			except:
				return HttpResponseBadRequest('Bad Request: Invalid max value\n')

		if not imax or imax > 50:
			imax = 50

		since = req.GET.get('since')
		since_id = None
		since_cursor = None
		if since:
			if since.startswith('id:'):
				since_id = since[3:]
			elif since.startswith('cursor:'):
				since_cursor = since[7:]
			else:
				return HttpResponseBadRequest('Bad Request: Invalid since value\n')

		# at the moment, cursor is identical to id
		item_id = None
		if since_id:
			item_id = since_id
		elif since_cursor:
			item_id = since_cursor

		if order == 'created':
			try:
				items, last_id = db.inbox_get_items_after(inbox_id, item_id, imax)
			except redis_ops.InvalidId:
				return HttpResponseBadRequest('Bad Request: Invalid id\n')
			except redis_ops.ObjectDoesNotExist:
				return HttpResponseNotFound('Not Found\n')
			except:
				return HttpResponse('Service Unavailable\n', status=503)

			if len(items) > 0:
				out = dict()
				out['last_cursor'] = last_id
				out_items = list()
				for i in items:
					out_items.append(_convert_item(i, not db.request_is_pending(inbox_id, i['id'])))
				out['items'] = out_items
				return HttpResponse(json.dumps(out) + '\n', content_type='application/json')

			if not grip.is_proxied(req, grip_proxies):
				return HttpResponse('Not Implemented\n', status=501)

			channel = gripcontrol.Channel(grip_prefix + 'inbox-' + inbox_id, last_id)
			theaders = dict()
			theaders['Content-Type'] = 'application/json'
			tbody = dict()
			tbody['last_cursor'] = last_id
			tbody['items'] = list()
			tbody_raw = json.dumps(tbody) + '\n'
			tresponse = gripcontrol.Response(headers=theaders, body=tbody_raw)
			instruct = gripcontrol.create_hold_response(channel, tresponse)
			return HttpResponse(instruct, content_type='application/grip-instruct')
		else: # -created
			try:
				items, last_id, eof = db.inbox_get_items_before(inbox_id, item_id, imax)
			except redis_ops.InvalidId:
				return HttpResponseBadRequest('Bad Request: Invalid id\n')
			except redis_ops.ObjectDoesNotExist:
				return HttpResponseNotFound('Not Found\n')
			except:
				return HttpResponse('Service Unavailable\n', status=503)

			out = dict()
			if not eof and last_id:
				out['last_cursor'] = last_id
			out_items = list()
			for i in items:
				out_items.append(_convert_item(i, not db.request_is_pending(inbox_id, i['id'])))
			out['items'] = out_items
			return HttpResponse(json.dumps(out) + '\n', content_type='application/json')
	else:
		return HttpResponseNotAllowed(['GET'])

def stream(req, inbox_id):
	if req.method == 'GET':
		try:
			db.inbox_get(inbox_id)
		except redis_ops.InvalidId:
			return HttpResponseBadRequest('Bad Request: Invalid id\n')
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
		except:
			return HttpResponse('Service Unavailable\n', status=503)

		if not grip.is_proxied(req, grip_proxies):
			return HttpResponse('Not Implemented\n', status=501)

		rheaders = dict()
		rheaders['Content-Type'] = 'text/plain'
		response = gripcontrol.Response(headers=rheaders, body='[opened]\n')

		instruct = gripcontrol.create_hold_stream(grip_prefix + 'inbox-' + inbox_id, response)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])
