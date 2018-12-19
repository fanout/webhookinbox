from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response

def _page(request, name, inbox_id=None):
	if settings.WHINBOX_API_BASE:
		api_base_uri = settings.WHINBOX_API_BASE
	else:
		api_base_uri = 'http://%s%s' % (request.META['HTTP_HOST'], '/api')

	ga_id = settings.GA_ID

	context = {
		'debug': settings.DEBUG,
		'api_base_uri': api_base_uri
	}
	if inbox_id:
		context['inbox_id'] = inbox_id
	if ga_id:
		context['ga_id'] = ga_id

	return render_to_response('website/%s.html' % name, context, context_instance=RequestContext(request))

def home(request):
	return _page(request, 'home')

def view(request, inbox_id):
	return _page(request, 'view', inbox_id=inbox_id)

def about(request):
	return _page(request, 'about')

def contact(request):
	return _page(request, 'contact')
