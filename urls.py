from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('webhookinbox.views',
	url(r'^$', 'root'),
	url(r'^allocate/$', 'allocate'),
	url(r'^a/(?P<alloc_id>[^/]+)/$', 'inbox'),
	url(r'^a/(?P<alloc_id>[^/]+)/refresh/$', 'refresh'),
	url(r'^a/(?P<alloc_id>[^/]+)/items/$', 'items'),
	url(r'^a/(?P<alloc_id>[^/]+)/stream/$', 'stream'),
)
