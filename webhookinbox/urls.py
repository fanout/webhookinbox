from django.conf.urls import include, url

urlpatterns = [
	url(r'', include('website.urls')),
	url(r'^api/', include('api.urls'))
]
