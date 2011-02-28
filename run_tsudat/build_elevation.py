"""Build the elevation data to run a tsunami inundation scenario 
for Victor Harbor, South Australia, Australia.

Input: elevation data from project.py
Output: pts file stored in project.topographies_dir 
The run_model.py is reliant on the output of this script.

"""

import os
from os.path import join

import anuga
import project
import anuga.utilities.log as log


def build_elevation():
    # Preparation of topographic data
    # Convert ASC 2 DEM 2 PTS using source data and store result in source data
    # Do for coarse and fine data
    # Fine pts file to be clipped to area of interest
    log.info('project.bounding_polygon=%s' % project.bounding_polygon)
    log.info('project.combined_elevation=%s'
             % project.combined_elevation)

    # Create Geospatial data from ASCII files
    geospatial_data = {}
    for filename in project.ascii_grid_filenames:
        absolute_filename = join(project.topographies_folder, filename)
        anuga.asc2dem(absolute_filename+'.asc',
                                      use_cache=False,
                                      verbose=False)
        anuga.dem2pts(absolute_filename+'.dem', use_cache=False, verbose=False)

        G_grid = anuga.geospatial_data.\
                     Geospatial_data(file_name=absolute_filename+'.pts',
                                     verbose=False)

        log.info('Clip geospatial object')
        geospatial_data[filename] = G_grid.clip(project.bounding_polygon)

    # Create Geospatial data from TXT files
    for filename in project.point_filenames:
        log.info(filename)
        absolute_filename = project.topographies_folder+'/'+str(filename)
        G_points = anuga.geospatial_data.\
                       Geospatial_data(file_name=absolute_filename,
                                       verbose=False)
        log.info('Clip geospatial object')
        geospatial_data[filename] = G_points.clip(project.bounding_polygon)

    #####
    # Combine, clip and export dataset 
    #####

    log.info('Add geospatial objects')
    G = None
    for key in geospatial_data:
        G += geospatial_data[key]

    log.info('Export combined DEM file')
    G.export_points_file(project.combined_elevation + '.pts')
    log.info('Do txt version too')

    # NEEDED?
    # Use for comparision in ARC
    G.export_points_file(project.combined_elevation + '.txt')
