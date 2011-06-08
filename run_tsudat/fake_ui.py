#!/usr/bin/env python

"""A program that behaves like the UI.

Usage: fake_ui <scenario> <where_run> <setup>

Where <scenario>  may be VH or BB
      <where_run> may be local or amazon
      <setup>     is either trial or final
"""

import os
import shutil
import json
import tempfile


# the base of the TsuDAT user directory structures
TsuDATBase = '/data'
TsuDATMux = '/media/1TB_USB3/Tsu-DAT_Data/earthquake_data'


def main(Setup):
    """Behave like the UI and run a TsuDAT simulation on EC2.
    
    The imported modules 'scenario' and 'run_tsudat' are used to
    get scenario and run location data.
    """

    # get all project/scenario/... data
    User = scenario.user
    Project = scenario.project
    Scenario = scenario.scenario
    Event = scenario.event
    WorkingDirectory = scenario.working_directory
    BoundingPolygon = scenario.bounding_polygon_file
    RawElevationFiles = scenario.elevation_data_list
    InteriorRegions = scenario.interior_regions_list
    InteriorHazardPoints = scenario.interior_hazard_points_file
    LandwardBoundary = scenario.landward_boundary_file
    GaugeFile = scenario.gauge_file
    CombinedElevationFile = scenario.combined_elevation_file
    RasterResolution = scenario.raster_resolution
    MeshFriction = scenario.mesh_friction
    InitialTide = scenario.initial_tide
    StartTime = scenario.start_time
    EndTime = scenario.end_time
    Smoothing = scenario.smoothing
    ExportArea = scenario.export_area
    BoundingPolygonMaxArea = scenario.bounding_polygon_maxarea
    ZoneNumber = scenario.zone_number
    LayersList = scenario.layers_list
    GetResultsMax = scenario.get_results_max
    GetTimeseries = scenario.get_timeseries
    GetSWW = scenario.getsww
    ForceRun = scenario.force_run
    Debug = scenario.debug

    STSFileStem = '%s' % Scenario
    STSFile = STSFileStem + '.sts'

    # the directory containing all data files required
    DataFilesDir = './fake_ui_files.%s' % Scenario

    # create the user working directory
    (user_dir, raw_elevations, boundaries, meshes, polygons, gauges,
     topographies) = run_tsudat.make_tsudat_dir(TsuDATBase, User, Project,
                                                Scenario, Setup, Event)

    # build the appropriate json data file
    (_, json_file) = tempfile.mkstemp(suffix='.json',
                                      prefix='fake_ui_', text=True)
    json_dict = {'user': User,
                 'project': Project,
                 'scenario': Scenario,
                 'setup': Setup,
                 'event_number': Event,
                 'working_directory': WorkingDirectory,
                 'user_directory': user_dir,
                 'mux_directory': TsuDATMux,
                 'initial_tide': InitialTide,
                 'start_time': StartTime,
                 'end_time': EndTime,
                 'smoothing': Smoothing,
                 'bounding_polygon_file': BoundingPolygon,
                 'raw_elevation_directory': raw_elevations,
                 'elevation_data_list': RawElevationFiles,
                 'combined_elevation_file': CombinedElevationFile,
                 'mesh_friction': MeshFriction,
                 'raster_resolution': RasterResolution,
                 'export_area': ExportArea,
                 'gauge_file': GaugeFile,
                 'bounding_polygon_maxarea': BoundingPolygonMaxArea,
                 'interior_regions_list': InteriorRegions,
                 'interior_hazard_points_file': InteriorHazardPoints,
                 'landward_boundary_file': LandwardBoundary,
                 'zone_number': ZoneNumber,
                 'layers_list': LayersList,
                 'get_results_max': GetResultsMax,
                 'get_timeseries': GetTimeseries,
                 'ascii_grid_filenames': [],
                 'sts_filestem': STSFileStem,
                 'getsww': GetSWW,          # if True, forces delivery of SWW files
                 'force_run': ForceRun,     # if True, *forces* a simulation
                 'debug': Debug}            # if True, forces DEBUG logging

    with open(json_file, 'w') as fd:
        json.dump(json_dict, fd, indent=2, separators=(',', ':'))

    # copy data files to correct places in user directory
    # maintain time/data stats
    for f in RawElevationFiles:
        shutil.copy2(os.path.join(DataFilesDir, 'raw_elevations', f),
                     raw_elevations)

    shutil.copy2(os.path.join(DataFilesDir, 'polygons', BoundingPolygon), polygons)
    for (_, f, _) in InteriorRegions:
        shutil.copy2(os.path.join(DataFilesDir, 'polygons', f), polygons)

    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', LandwardBoundary), boundaries)
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', InteriorHazardPoints), boundaries)
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', STSFile), boundaries)

    shutil.copy2(os.path.join(DataFilesDir, 'gauges', GaugeFile), gauges)

    # fudge for BB
    if CombinedElevationFile:
        shutil.copy2(os.path.join(DataFilesDir, 'topographies', CombinedElevationFile), topographies)

    # now run the simulation
    gen_files = run_tsudat.run_tsudat(json_file)

    # remove temporary files
    os.remove(json_file)
    

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        print('usage: %s <scenario> <where_run> <setup>' % sys.argv[0])
        sys.exit(10)

    scenario = sys.argv[1]
    scenario_lower = scenario.lower()

    where_run = sys.argv[2]
    where_run_lower = where_run.lower()

    setup = sys.argv[3]
    setup_lower = setup.lower()

    error = False
    try:
        exec('import scenario_%s as scenario' % scenario_lower)
    except ImportError:
        print('Unknown scenario: %s' % scenario)
        error = True

    try:
        exec('import run_tsudat_%s as run_tsudat' % where_run_lower)
    except ImportError:
        print('Unknown run location: %s' % where_run)
        error = True

    if setup_lower not in ['trial', 'final']:
        print("<setup> must be either 'trial' or 'final'")
        error = True

    if error:
        sys.exit(10)

    main(setup_lower)
