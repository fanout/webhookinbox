from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('webhookinbox.website.views',
	url(r'^$', 'home'),
	url(r'^view/(?P<inbox_id>[^/]+)/$', 'view'),
	url(r'^about/$', 'about'),
	url(r'^contact/$', 'contact'),
)
