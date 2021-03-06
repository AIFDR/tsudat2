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
    (r'^polygon_from_csv/$', 'polygon_from_csv'),
    (r'^internal_polygon_types/$', 'internal_polygon_types'),
    (r'^internal_polygon/$', 'internal_polygon'),
    (r'^internal_polygon/(?P<id>[0-9]+)/$', 'internal_polygon'),
    (r'^gauge_point/$', 'gauge_point'),
    (r'^gauge_point/(?P<id>[0-9]+)/$', 'gauge_point'),
    (r'^scenario/$', 'scenario'),
    (r'^scenario_list/$', 'scenario_list'),
    (r'^scenario/(?P<id>[0-9]+)/$', 'scenario'),
    (r'^scenario_info/(?P<id>[0-9]+)/$', 'scenario_info'),
    (r'^layer/$', 'layer'),
    (r'^layer/(?P<uuid>[\w]{8}(-[\w]{4}){3}-[\w]{12})/$', 'layer'),
    (r'^data_set/$', 'data_set'),
    (r'^data_set/(?P<id>[0-9]+)/$', 'data_set'),
    (r'^project_data_set/$', 'project_data_set'),
    (r'^project_data_set/(?P<id>[0-9]+)/$', 'project_data_set'),
    (r'^download_waveform/$', 'download_waveform'),
    (r'^run_scenario/(?P<scenario_id>[0-9]+)/$', 'run_scenario'),
    (r'^download_scenario/(?P<scenario_id>[0-9]+)/$', 'download_scenario'),
    (r'^disclaimer/$', 'disclaimer'),
    (r'^hp_rp_style.xml$', 'hazard_point_style'),
    (r'^about/$', 'about'),
)
