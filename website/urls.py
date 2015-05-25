from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.home, name='home'),
	url(r'^view/(?P<inbox_id>[^/]+)/$', views.view, name='view'),
	url(r'^about/$', views.about, name='about'),
	url(r'^contact/$', views.contact, name='contact')
]
