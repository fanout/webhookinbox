from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class OptionsMiddleware(MiddlewareMixin):
	def process_request(self, request):
		if request.method == 'OPTIONS':
			return HttpResponse()
