#!/usr/bin/env python

"""
Data for VictorHarbour
"""

# all the user/project/scenario data
user = 'user'
project = 'project'
scenario = 'BatemansBay'
event = 58348

# the data files
bounding_polygon_file = 'bounding_polygon.csv'
elevation_data_list = []
#interior_regions_list = [['aoi', 'area_of_interest.csv', None],
interior_regions_list = [['aoi', 'aoi.csv', None],
                         ['friction', 'mesh_friction_outer.csv', 0.05],
                         ['friction', 'mesh_friction_inner.csv', 0.1],
                         ['resolution', 'area_of_significance.csv', 2500],
                         ['resolution', 'shallow_water.csv', 10000]]
interior_hazard_points_file = 'interior_hp.csv'
landward_boundary_file = 'landward_boundary.csv'
gauge_file = 'gauges.csv'
combined_elevation_file = 'combined_elevation.pts'

# simulation parameters
initial_tide = 1.0
start_time = 0
end_time = 27000
smoothing = 0.1
raster_resolution = 20
mesh_friction = 0.01
layers_list = ['stage', 'depth']
export_area = 'AOI'
get_results_max = True
get_timeseries = True
bounding_polygon_maxarea = 100000
zone_number = 56

# miscellaneous stuff
working_directory = '/tmp/tsudat'

getsww = True
force_run = True
debug = True

