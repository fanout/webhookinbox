from django.urls import include, re_path

urlpatterns = [
	re_path(r'', include('website.urls')),
	re_path(r'^api/', include('api.urls'))
]
