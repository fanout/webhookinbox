from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('webhookinbox.api.views',
	url(r'^$', 'root'),
	url(r'^create/$', 'create'),
	url(r'^i/(?P<inbox_id>[^/]+)/$', 'inbox'),
	url(r'^i/(?P<inbox_id>[^/]+)/refresh/$', 'refresh'),
	url(r'^i/(?P<inbox_id>[^/]+)/respond/(?P<item_id>[^/]+)/$', 'respond'),
	url(r'^i/(?P<inbox_id>[^/]+)/in/', 'hit'),
	url(r'^i/(?P<inbox_id>[^/]+)/items/$', 'items'),
	url(r'^i/(?P<inbox_id>[^/]+)/stream/$', 'stream'),
)
