from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.root, name='root'),
	url(r'^create/$', views.create, name='create'),
	url(r'^i/(?P<inbox_id>[^/]+)/$', views.inbox, name='inbox'),
	url(r'^i/(?P<inbox_id>[^/]+)/refresh/$', views.refresh, name='refresh'),
	url(r'^i/(?P<inbox_id>[^/]+)/respond/(?P<item_id>[^/]+)/$', views.respond, name='respond'),
	url(r'^i/(?P<inbox_id>[^/]+)/in/', views.hit, name='hit'),
	url(r'^i/(?P<inbox_id>[^/]+)/items/$', views.items, name='items'),
	url(r'^i/(?P<inbox_id>[^/]+)/stream/$', views.stream, name='stream')
]
