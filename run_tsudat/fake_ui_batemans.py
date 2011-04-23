#!/usr/bin/env python

"""A program that behaves like the UI."""

import os
import shutil
import json
import tempfile

import run_tsudat_batemans as run_tsudat


# the base of the TsuDAT user directory structures
TsuDATBase = '/tmp/tsudat'

# all the user/project/scenario data
User = 'user'
Project = 'project'
Scenario = 'BatemansBay'
Setup = 'trial'
Event = 58348

# the directory containing all data files required
DataFilesDir = './fake_ui_files.%s' % Scenario

# the data files
BoundingPolygon = 'bounding_polygon.csv'
RawElevationFiles = []
InteriorRegions = [['area_of_interest.csv', 500],
                   ['area_of_significance.csv', 2500],
                   ['shallow_water.csv', 10000]]
UrsOrder = 'urs_order.csv'
LandwardBoundary = 'landward_boundary.csv'

STSFile = '%s.sts' % Scenario

GaugesFinal = 'gauges.csv'

MeshFile = 'meshes.msh'

# pre-generated combined elevation file
Elevation = 'combined_elevation.pts'



def main():
    """Behave like the UI and run a TsuDAT simulation locally."""

    # build the appropriate json data file
    (_, json_file) = tempfile.mkstemp(suffix='.json',
                                      prefix='fake_ui_', text=True)
    json_dict = {'user': User,
                 'project': Project,
                 'scenario_name': Scenario,
                 'setup': Setup,
                 'event': Event,
                 'tide': 1.0,
                 'start_time': 0,
                 'end_time': 27000,
                 'smoothing': 0.1,
                 'bounding_polygon': BoundingPolygon,
                 'elevation_data': RawElevationFiles,
                 'mesh_friction': 0.01,
                 'raster_resolution': 250,
                 'layers': ['stage', 'depth'],
                 'area': ['All'],
                 'get_results_max': True,
                 'get_timeseries': True,
                 'gauges': GaugesFinal,
                 'mesh_file': MeshFile,
                 'interior_regions_data': InteriorRegions,
                 'bounding_polygon_maxarea': 100000,
                 'urs_order': UrsOrder,
                 'landward_boundary': LandwardBoundary,
                 'ascii_grid_filenames': [],
                 'zone': 54,
                 'xminAOI': 239690,
                 'xmaxAOI': 255206,
                 'yminAOI': 6036317,
                 'ymaxAOI': 6050529,
                 'force_run': False, # if True, *forces* a simulation
                 'debug': True}	# if True, forces DEBUG logging
    with open(json_file, 'w') as fd:
        json.dump(json_dict, fd, indent=2, separators=(',', ':'))

    # create the user working directory
    (run_dir, raw_elevations, boundaries, meshes,
     polygons, gauges) = run_tsudat.make_tsudat_dir(TsuDATBase, User, Project,
                                                    Scenario, Setup, Event)

    # copy data files to correct places in user directory
    # maintain time/data stats
    for f in RawElevationFiles:
        shutil.copy2(os.path.join(DataFilesDir, 'raw_elevations', f),
                     raw_elevations)

    shutil.copy2(os.path.join(DataFilesDir, 'polygons', BoundingPolygon), polygons)
    for (f, _) in InteriorRegions:
        shutil.copy2(os.path.join(DataFilesDir, 'polygons', f), polygons)

    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', LandwardBoundary), boundaries)
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', UrsOrder), boundaries)
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', STSFile), boundaries)

    shutil.copy2(os.path.join(DataFilesDir, 'gauges', GaugesFinal), gauges)

    # pre-generated combined elevation data file
    topo = os.path.join(os.path.dirname(gauges), 'topographies')
    shutil.copy2(os.path.join(DataFilesDir, 'topographies', Elevation), topo)

    # now run the simulation
    gen_files = run_tsudat.run_tsudat(json_file)

    # remove temporary files
    os.remove(json_file)
    

if __name__ == '__main__':
    main()
