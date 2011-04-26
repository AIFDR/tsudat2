#!/usr/bin/env python

"""A program that behaves like the UI.

Run the Victor Harbour simulation.
"""

import os
import shutil
import json
import tempfile

import run_tsudat_amazon as run_tsudat


# the base of the TsuDAT user directory structures
TsuDATBase = '/tmp/tsudat'
#TsuDATMux = '/data_area/Tsu-DAT_1.0/Tsu-DAT_Data/earthquake_data'
TsuDATMux = '/media/1TB_USB3/Tsu-DAT_Data/earthquake_data'

# all the user/project/scenario data
User = 'user'
Project = 'project'
Scenario = 'VictorHarbour'
Setup = 'trial'
Event = 58342

# the directory containing all data files required
DataFilesDir = './fake_ui_files.%s' % Scenario

# the data files
BoundingPolygon = 'bounding_polygon.csv'
RawElevationFiles = ['250m_final.csv', 'shallow_water.csv', 'aoi.csv']
InteriorRegions = [['area_of_interest.csv', 500],
                   ['area_of_significance.csv', 2500],
                   ['shallow_water.csv', 10000]]
UrsOrder = 'urs_order.csv'
LandwardBoundary = 'landward_boundary.csv'

STSFileStem = '%s' % Scenario
STSFile = STSFileStem + '.sts'

GaugeFile = 'gauges_final.csv'

MeshFile = '%s.msh' % Scenario

# pre-generated combined elevation file
CombinedElevationFile = None


def main():
    """Behave like the UI and run a TsuDAT simulation on EC2."""

    # build the appropriate json data file
    (_, json_file) = tempfile.mkstemp(suffix='.json',
                                      prefix='fake_ui_', text=True)
    json_dict = {'user': User,
                 'project': Project,
                 'scenario': Scenario,
                 'setup': Setup,
                 'event_number': Event,
                 'working_directory': TsuDATBase,
                 'mux_directory': TsuDATMux,
                 'initial_tide': 0.0,
                 'start_time': 0,
                 'end_time': 27000,
                 'smoothing': 0.1,
                 'bounding_polygon_file': BoundingPolygon,
                 'elevation_data_list': RawElevationFiles,
                 'combined_elevation_file': CombinedElevationFile,
                 'mesh_friction': 0.01,
                 'raster_resolution': 250,
                 'layers': ['stage', 'depth'],
                 'area': ['All'],
                 'get_results_max': True,
                 'get_timeseries': True,
                 'gauge_file': GaugeFile,
                 'mesh_file': MeshFile,
                 'interior_regions_list': InteriorRegions,
                 'bounding_polygon_maxarea': 100000,
                 'urs_order_file': UrsOrder,
                 'landward_boundary_file': LandwardBoundary,
                 'ascii_grid_filenames': [],
                 'sts_filestem': STSFileStem,
                 'zone_number': 54,
                 'force_run': True, # if True, *forces* a simulation
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

    shutil.copy2(os.path.join(DataFilesDir, 'gauges', GaugeFile), gauges)

    # now run the simulation
    gen_files = run_tsudat.run_tsudat(json_file)

    # remove temporary files
    os.remove(json_file)
    

if __name__ == '__main__':
    main()
