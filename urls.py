from django.conf.urls.defaults import *
from staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.contrib import admin

PROXY_DOMAIN = "localhost:8080/geoserver"
PROXY_FORMAT = u"http://%s/%s" % (PROXY_DOMAIN, u"%s")

def build_pattern(name, action="show"):
        return url("^%s/(?P<object_id>\d+)/%s$" % (name, action),
            "%s_%s" % (action, name),
            name="%s_%s" % (action, name))

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'tsudat.views.index', name='tsudat-index'),
    (r'^admin/', include(admin.site.urls)),
    (r'^proxy/', 'proxy.views.proxy'),
    (r'^geoserver/','proxy.views.geoserver'),
    (r'^tsudat/', include('tsudat.urls')),
)

if settings.SERVE_MEDIA:
    urlpatterns += staticfiles_urlpatterns()
