from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response

def _page(request, name, inbox_id=None):
	assert(settings.WHINBOX_API_BASE)
	context = {
		'api_base_uri': settings.WHINBOX_API_BASE,
	}
	if inbox_id:
		context['inbox_id'] = inbox_id
	return render_to_response('website/%s.html' % name, context, context_instance=RequestContext(request))

def home(request):
	return _page(request, 'home')

def view(request, inbox_id):
	return _page(request, 'view', inbox_id=inbox_id)

def about(request):
	return _page(request, 'about')

def contact(request):
	return _page(request, 'contact')
