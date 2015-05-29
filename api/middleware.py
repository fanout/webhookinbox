from django.http import HttpResponse

class OptionsMiddleware:
	def process_request(self, request):
		if request.method == 'OPTIONS':
			return HttpResponse()
