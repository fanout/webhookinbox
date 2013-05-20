import json
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseNotAllowed
import redis_ops

redis_ops.set_config('wi-', 'localhost', 6379)

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
		redis_ops.inbox_refresh(alloc_id)
		# TODO: save item, publish updates
		return HttpResponse('Refreshed\n')
	elif req.method == 'DELETE':
		redis_ops.inbox_delete(alloc_id)
		return HttpResponse('Deleted\n')
	else:
		return HttpResponseNotAllowed(['GET', 'DELETE'])

def refresh(req, alloc_id):
	if req.method == 'POST':
		ttl = req.POST.get('ttl')
		if ttl is not None:
			ttl = int(ttl)
		redis_ops.inbox_refresh(alloc_id, ttl)
	else:
		return HttpResponseNotAllowed(['POST'])

def items(req, alloc_id):
	# TODO: refresh and return items
	pass

def stream(req, alloc_id):
	# TODO: just return a grip stream instruct
	pass
