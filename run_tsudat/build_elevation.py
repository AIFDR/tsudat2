import os
from os.path import join

import anuga
import project
import anuga.utilities.log as log


def build_elevation():
    """Create combined elevation data.

    Combine all raw elevation data and clip to bounding polygon.
    """

    # Create Geospatial data from ASCII files
    geospatial_data = {}
    for filename in project.ascii_grid_filenames:
        log.info('Reading elevation ASC file %s' % filename)
        absolute_filename = join(project.raw_elevation_folder, filename)
        anuga.asc2dem(absolute_filename+'.asc',
                      use_cache=False, verbose=False)
        anuga.dem2pts(absolute_filename+'.dem', use_cache=False, verbose=False)

        G_grid = anuga.geospatial_data.\
                     Geospatial_data(file_name=absolute_filename+'.pts',
                                     verbose=False)

        geospatial_data[filename] = G_grid.clip(project.bounding_polygon)

    # Create Geospatial data from TXT files
    for filename in project.point_filenames:
        log.info('Reading elevation TXT file %s' % filename)
        absolute_filename = os.path.join(project.raw_elevation_folder, filename)
        G_points = anuga.geospatial_data.\
                       Geospatial_data(file_name=absolute_filename,
                                       verbose=False)

        geospatial_data[filename] = G_points.clip(project.bounding_polygon)

    #####
    # Combine, clip and export dataset 
    #####

    G = None
    for key in geospatial_data:
        G += geospatial_data[key]

    G.export_points_file(project.combined_elevation + '.pts')

    # Use for comparision in ARC
    G.export_points_file(project.combined_elevation + '.txt')
