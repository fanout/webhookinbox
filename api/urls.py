from django.urls import re_path
from . import views

urlpatterns = [
	re_path(r'^$', views.root, name='root'),
	re_path(r'^create/$', views.create, name='create'),
	re_path(r'^i/(?P<inbox_id>[^/]+)/$', views.inbox, name='inbox'),
	re_path(r'^i/(?P<inbox_id>[^/]+)/refresh/$', views.refresh, name='refresh'),
	re_path(r'^i/(?P<inbox_id>[^/]+)/respond/(?P<item_id>[^/]+)/$', views.respond, name='respond'),
	re_path(r'^i/(?P<inbox_id>[^/]+)/in/', views.hit, name='hit'),
	re_path(r'^i/(?P<inbox_id>[^/]+)/items/$', views.items, name='items'),
	re_path(r'^i/(?P<inbox_id>[^/]+)/stream/$', views.stream, name='stream')
]
