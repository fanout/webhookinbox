from django.template import RequestContext
from django.shortcuts import render_to_response

def home(request):
	return render_to_response('website/home.html', {}, context_instance=RequestContext(request))

def view(request, inbox_id):
	return render_to_response('website/view.html', { 'inbox_id': inbox_id }, context_instance=RequestContext(request))

def about(request):
	return render_to_response('website/about.html', {}, context_instance=RequestContext(request))
