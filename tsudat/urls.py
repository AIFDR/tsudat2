from django.conf.urls.defaults import *

urlpatterns = patterns('tsudat.views',
    (r'^return_periods/$', 'return_periods'),
    (r'^hazard_points/$', 'hazard_points'),
    (r'^source_zones/$', 'source_zones'),
    (r'^sub_faults/$', 'sub_faults'),
    (r'^events/$', 'events'),
)
