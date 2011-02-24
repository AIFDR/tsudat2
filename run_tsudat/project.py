"""Sample project.py - leading into tsudat2."""

import os
import sys
import time

'''
# this is how we might get tsudat2 UI data into the system
# exec() is a little ugly, think of another way to do this
import tsudat_data
for _ in dir(tsudat_data):
    if not _.startswith('__'):
        exec('%s = tsudat_data.%s' (_, _))
del _, data

# or we could just do:
user_name = data.user_name
tide = data.tide
finaltime = data.end_time
# etc, then
del data
# which would give us a chance to rename data as well
'''


#####
# All values from UI.
# We might get them from 'import tsudat_data' above, but for now ...
#####

# step 0 (login info)
user_name = 'fred'              # unique login name from UI

# step 1
#######################################################################
tide = 0.0                      # 'tide' from UI
starttime = 0                   # 'start time' from UI
finaltime = 40                  # 'end time' from UI
alpha = 0.1                     # 'smoothing' from UI

# step 2
#######################################################################
# polygon - 'simulation area'
# BOUNDING POLYGON - for data clipping and estimate of triangles in mesh
# Format for points easting,northing (no header)
bounding_polygon_filename = 'bounding_polygon.csv'
bounding_polygon_maxarea = 100000

# float - 'mesh_resolution'

# ?? - 'elevation data'
# ELEVATION DATA
# Format for point is x,y,elevation (with header)
point_filenames = ['250m_final.csv', 'shallow_water.csv', 'aoi.csv']
# Format for ascii grids, as produced in ArcGIS + a projection file
ascii_grid_filenames = []

# ?? 'internal polygons'
friction = 0.01                 # 'mesh friction' from UI

# step 3
#######################################################################
event_number = 58342            # 'event ID' from UI

# step 4
#######################################################################
scenario_name = 'victor_harbor' # 'scenario name' in UI
# 'clipping polygon' - export results within this
UI_cell_size = 250              # 'raster resolution' in UI
UI_var = ['stage', 'depth']     # 'layers' in UI
# boolean - maximum value over simulation
UI_get_results_max = True
UI_get_timeseries = True
UI_area = ['All']               # ?? in UI

# 'gauge points' - .csv file?
# GAUGES - for creating timeseries at a specific point
# Format easting,northing,name,elevation (with header)
gauges_filename = 'gauges_final.csv'

#-------------------------------------------------------------------------------
# Directory setup
#-------------------------------------------------------------------------------

# these will go away
state = 'south_australia'
scenario_folder = 'victor_harbor_tsunami_scenario_2010'

#-------------------------------------------------------------------------------
# Initial Conditions
#-------------------------------------------------------------------------------

# where is rhis in the UI?
setup = 'trial'         # This can be one of: trial, basic, final

#-------------------------------------------------------------------------------
# Output filename
#
# The output filename should be unique between different runs on different data.
# The list of items below will be used to create a file in the output directory.
# The user name and time+date will be automatically added.  For example,
#     [setup, event_number]
# will result in a filename like
#     20090212_091046_run_final_27283_wilsor
#-------------------------------------------------------------------------------

output_comment = [setup, event_number]

#-------------------------------------------------------------------------------
# Input Data
#-------------------------------------------------------------------------------


# INTERIOR REGIONS -  for designing the mesh
# Format for points easting,northing (no header)

# For high res model
interior_regions_data = [['area_of_interest.csv', 500],
                         ['area_of_significance.csv', 2500],
                         ['shallow_water.csv', 10000]]

# LAND - used to set the initial stage/water to be offcoast only
# Used in run_model.py.  Format for points easting,northing (no header)
land_initial_conditions_filename = []                                  

# Thinned ordering file from Hazard Map (geographic)
# Format is index,latitude,longitude (with header)
urs_order_filename = 'urs_order.csv'

# Landward bounding points
# Format easting,northing (no header)
landward_boundary_filename = 'landward_boundary.csv'

# MUX input filename.
# If a meta-file from EventSelection is used, set 'multi-mux' to True.
# If a single MUX stem filename (*.grd) is used, set 'multi-mux' to False.
mux_input_filename = 'event.list'
multi_mux = True

zone = 54		# IS THIS USED?

#-------------------------------------------------------------------------------
# Clipping regions for export to asc and regions for clipping data
# Final inundation maps should only be created in regions of the finest mesh
#-------------------------------------------------------------------------------

# ADO WE NEED TO COMPUTE THIS FROM AOI?
xminAOI = 281000
xmaxAOI = 309000
yminAOI = 6056000
ymaxAOI = 6069000

################################################################################
################################################################################
####         NOTE: NOTHING WOULD NORMALLY CHANGE BELOW THIS POINT.          ####
################################################################################
################################################################################

# THESE WILL BE REPLACED BY TSUDAT2 CONFIGURATION VALUES
# Environment variable names.
# The inundation directory, not the data directory.
ENV_INUNDATIONHOME = 'INUNDATIONHOME'

# Path to MUX data
ENV_MUXHOME = 'MUXHOME'

#-------------------------------------------------------------------------------
# Output Elevation Data
#-------------------------------------------------------------------------------

# Output filename for elevation
# this is a combination of all the data generated in build_elevation.py
combined_elevation_basename = scenario_name + '_combined_elevation'

#-------------------------------------------------------------------------------
# Directory Structure
#-------------------------------------------------------------------------------

# determines time for setting up output directories
ltime = time.strftime('%Y%m%d_%H%M%S', time.localtime()) 
build_time = ltime + '_build'
run_time = ltime + '_run_'

# create paths generated from environment variables.
home = os.path.join(os.getenv(ENV_INUNDATIONHOME), 'data') # path to data folder
muxhome = os.getenv(ENV_MUXHOME)
    
# check various directories/files that must exist
anuga_folder = os.path.join(home, state, scenario_folder, 'anuga')
topographies_folder = os.path.join(anuga_folder, 'topographies')
polygons_folder = os.path.join(anuga_folder, 'polygons')
boundaries_folder = os.path.join(anuga_folder, 'boundaries')
output_folder = os.path.join(anuga_folder, 'outputs')
gauges_folder = os.path.join(anuga_folder, 'gauges')
meshes_folder = os.path.join(anuga_folder, 'meshes')
event_folder = os.path.join(boundaries_folder, str(event_number))

# MUX data files
# Directory containing the MUX data files to be used with EventSelection.
mux_data_folder = os.path.join(muxhome, 'mux')

#-------------------------------------------------------------------------------
# Location of input and output data
#-------------------------------------------------------------------------------

# Convert the user output_comment to a string for run_model.py
output_comment = ('_'.join([str(x) for x in output_comment if x != user_name])
                  + '_' + user_name)

# The absolute pathname of the all elevation, generated in build_elevation.py
combined_elevation = os.path.join(topographies_folder,
                                  combined_elevation_basename)

# The absolute pathname of the mesh, generated in run_model.py
meshes = os.path.join(meshes_folder, scenario_name) + '.msh'

# The pathname for the urs order points, used within build_urs_boundary.py
urs_order = os.path.join(boundaries_folder, urs_order_filename)

# The absolute pathname for the landward points of the bounding polygon,
# Used within run_model.py)
landward_boundary = os.path.join(boundaries_folder, landward_boundary_filename)

# The absolute pathname for the .sts file, generated in build_boundary.py
event_sts = os.path.join(event_folder, scenario_name)

# The absolute pathname for the output folder names
# Used for build_elevation.py
output_build = os.path.join(output_folder, build_time) + '_' + str(user_name) 
# Used for run_model.py
output_run = os.path.join(output_folder, run_time) + output_comment 
# Used by post processing
output_run_time = os.path.join(output_run, scenario_name) 

# The absolute pathname for the gauges file
gauges = os.path.join(gauges_folder, gauges_filename)       

# full path to where MUX files (or meta-files) live
mux_input = os.path.join(event_folder, mux_input_filename)

