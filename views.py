import json
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseNotAllowed
import gripcontrol
import redis_ops

redis_ops.set_config('wi-', 'localhost', 6379)

pub = gripcontrol.GripPubControl('http://localhost:5561')

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
	if req.method == 'GET':
		try:
			redis_ops.inbox_refresh(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		# TODO: save item
		# TODO: headers, body/body-bin
		item = dict()
		item['type'] = 'normal'
		item['path'] = req.path
		query = req.META.get('QUERY_STRING')
		if query:
			item['query'] = query

		pub.publish_http_stream_async('inbox-stream-' + alloc_id, json.dumps(item) + '\n')
		return HttpResponse('Refreshed\n')
	elif req.method == 'DELETE':
		try:
			redis_ops.inbox_delete(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		return HttpResponse('Deleted\n')
	else:
		return HttpResponseNotAllowed(['GET', 'DELETE'])

def refresh(req, alloc_id):
	if req.method == 'POST':
		ttl = req.POST.get('ttl')
		if ttl is not None:
			ttl = int(ttl)

		try:
			redis_ops.inbox_refresh(alloc_id, ttl)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')
	else:
		return HttpResponseNotAllowed(['POST'])

def items(req, alloc_id):
	# TODO: refresh and return items
	pass

def stream(req, alloc_id):
	if req.method == 'GET':
		try:
			redis_ops.inbox_get(alloc_id)
		except redis_ops.ObjectDoesNotExist:
			return HttpResponseNotFound('Not Found\n')

		instruct = gripcontrol.create_hold_stream('inbox-stream-' + alloc_id)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])
