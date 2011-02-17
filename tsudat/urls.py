from django.conf.urls.defaults import *

urlpatterns = patterns('tsudat.views',
    (r'^return_periods/$', 'return_periods'),
    (r'^return_period/$', 'return_period'),
    (r'^hazard_points/$', 'hazard_points'),
    (r'^source_zones/$', 'source_zones'),
    (r'^source_zone/$', 'source_zone'),
    (r'^sub_faults/$', 'sub_faults'),
    (r'^events/$', 'events'),
    (r'^wave_height/$', 'wave_height'),
    (r'^project/$', 'project'),
    (r'^project/(?P<id>[0-9]+)/$', 'project'),
    (r'^internal_polygon/$', 'internal_polygon'),
    (r'^internal_polygon/(?P<id>[0-9]+)/$', 'internal_polygon'),
)
