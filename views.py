from base64 import b64encode
import json
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed
import pubcontrol
import gripcontrol
import redis_ops

redis_ops.set_config('wi-', 'localhost', 6379)

pub = gripcontrol.GripPubControl('http://localhost:5561')

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
	headers = list()
	for h in raw_headers:
		name = _convert_header_name(h[0])
		if not _ignore_header(name):
			headers.append([name, h[1]])
	item['headers'] = headers
	if len(req.raw_post_data) > 0:
		try:
			# if the body is valid utf-8, then store as text
			body = req.raw_post_data.decode('utf-8')
			item['body'] = body
		except:
			# else, store as binary
			item['body-bin'] = b64encode(req.raw_post_data)

	return item

def root(req):
	return HttpResponseNotFound('Not Found\n')

def allocate(req):
	if req.method == 'POST':
		host = req.META['HTTP_HOST']
		ttl = req.POST.get('ttl')
		if ttl is not None:
			ttl = int(ttl)
		if ttl is None:
			ttl = 60
		alloc_id = redis_ops.inbox_create(ttl)
		out = dict()
		out['id'] = alloc_id
		out['target'] = 'http://' + host + '/a/' + alloc_id + '/'
		out['ttl'] = ttl
		return HttpResponse(json.dumps(out) + '\n')
	else:
		return HttpResponseNotAllowed(['POST'])

def inbox(req, alloc_id):
	if req.method == 'DELETE':
		try:
			redis_ops.inbox_delete(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		return HttpResponse('Deleted\n')
	else:
		try:
			redis_ops.inbox_get(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		# pubsubhubbub verify request?
		hub_challenge = req.GET.get('hub.challenge')

		item = _req_to_item(req)
		if hub_challenge:
			item['type'] = 'hub-verify'
		else:
			item['type'] = 'normal'

		item_id, prev_id = redis_ops.inbox_append_item(alloc_id, item)

		hr = dict()
		hr['last_cursor'] = item_id
		hr['items'] = [item]
		hr_json = json.dumps(hr) + '\n'
		hs_json = json.dumps(item) + '\n'
		formats = list()
		formats.append(gripcontrol.HttpResponseFormat(body=hr_json))
		formats.append(gripcontrol.HttpStreamFormat(hs_json))
		item = pubcontrol.Item(formats, item_id, prev_id)
		pub.publish_async('inbox-' + alloc_id, item)

		if hub_challenge:
			return HttpResponse(hub_challenge)
		else:
			return HttpResponse('Ok\n')

def refresh(req, alloc_id):
	if req.method == 'POST':
		ttl = req.POST.get('ttl')
		if ttl is not None:
			ttl = int(ttl)

		try:
			redis_ops.inbox_refresh(alloc_id, ttl)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		return HttpResponse('Refreshed\n')
	else:
		return HttpResponseNotAllowed(['POST'])

def items(req, alloc_id):
	if req.method == 'GET':
		try:
			redis_ops.inbox_refresh(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		since = req.GET.get('since')
		if since:
			if not since.startswith('cursor:'):
				return HttpResponseBadRequest('Bad Request: Invalid since value\n')

			item_id = since[7:]

			items, last_id = redis_ops.inbox_get_items_after(alloc_id, item_id)
			if len(items) > 0:
				out = dict()
				out['last_cursor'] = last_id
				out['items'] = items
				return HttpResponse(json.dumps(out) + '\n')
		else:
			last_id = redis_ops.inbox_get_last_id(alloc_id)

		channel = gripcontrol.Channel('inbox-' + alloc_id, last_id)
		hr = dict()
		hr['last_cursor'] = last_id
		hr['items'] = list()
		hr_json = json.dumps(hr) + '\n'
		timeout_response = gripcontrol.Response(body=hr_json)
		instruct = gripcontrol.create_hold_response(channel, timeout_response)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])

def stream(req, alloc_id):
	if req.method == 'GET':
		try:
			redis_ops.inbox_get(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		instruct = gripcontrol.create_hold_stream('inbox-' + alloc_id)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])
