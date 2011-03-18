import os, sys
import logging
import shutil
import simplejson as json
import tempfile

from django import db
from django.contrib.auth.models import User
from django.conf import settings

from tsudat.models import *
from celery.decorators import task

from run_tsudat import run_tsudat

try:
    from notification import models as notification
except ImportError:
    notification = None

logger = logging.getLogger("tsudat2.tsudat.tasks")

@task
def run_tsudat_simulation(user, scenario_id):
    scenario = Scenario.objects.get(id=scenario_id)
        
    # the base of the TsuDAT user directory structures
    # from settings.py
    TsuDATBase = settings.TSUDAT_BASE_DIR

    ProjectFilesDir = TsuDATBase + '/run'
    # the directory containing all data files required
    DataFilesDir = '%s/fake_ui_files.%s' % (TsuDATBase, scenario.name)

    # the data files
    project_geom = scenario.project.geom

    #Need to actually determine the right UTM Zone
    project_geom.transform(32756)

    BoundingPolygon = 'bounding_polygon.csv'
    RawElevationFiles = []
    InteriorRegions = [['area_of_interest.csv', 500],
                       ['area_of_significance.csv', 2500],
                       ['shallow_water.csv', 10000]]
    UrsOrder = 'urs_order.csv'
    LandwardBoundary = 'landward_boundary.csv'

    STSFile = '%s.sts' % scenario.name

    GaugesFinal = 'gauges.csv'

    MeshFile = 'meshes.msh'

    # pre-generated combined elevation file
    Elevation = 'combined_elevation.pts'

    # build the appropriate json data file
    json_file = os.path.join(ProjectFilesDir, '%s.%s.json' % (scenario.name, scenario.project.name))
               
    json_dict = {'user': user.username,
                 'project': scenario.project.name,
                 'scenario_name': scenario.name,
                 'setup': scenario.model_setup,
                 'event': scenario.event.tsudat_id,
                 'tide': scenario.initial_tidal_stage,
                 'start_time': scenario.start_time,
                 'end_time': scenario.end_time,
                 'smoothing': scenario.smoothing_param,
                 'bounding_polygon': BoundingPolygon,
                 'elevation_data': RawElevationFiles,
                 'mesh_friction': scenario.default_friction_value,
                 'raster_resolution': 250,
                 'layers': ['stage', 'depth'],
                 'area': ['All'],
                 'get_results_max': True,
                 'get_timeseries': True,
                 'gauges': GaugesFinal,
                 'meshfile': MeshFile,
                 'interior_regions_data': InteriorRegions,
                 'bounding_polygon_maxarea': 100000,
                 'urs_order': UrsOrder,
                 'landward_boundary': LandwardBoundary,
                 'ascii_grid_filenames': [],
                 'zone': 54,
                 'xminAOI': project_geom.extent[0],
                 'xmaxAOI': project_geom.extent[1],
                 'yminAOI': project_geom.extent[2],
                 'ymaxAOI': project_geom.extent[3],
                 'force_run': False, # if True, *forces* a simulation
                 'debug': True}	# if True, forces DEBUG logging
    with open(json_file, 'w') as fd:
        json.dump(json_dict, fd, indent=2, separators=(',', ':'))

    # create the user working directory
    (raw_elevations, boundaries, meshes,
     polygons, gauges) = run_tsudat.make_tsudat_dir(TsuDATBase + '/run', user.username, scenario.project.name,
                                                    scenario.name, scenario.model_setup, scenario.event.tsudat_id)

    # copy data files to correct places in user directory
    # maintain time/data stats
    for f in RawElevationFiles:
        shutil.copy2(os.path.join(DataFilesDir, 'raw_elevations', f),
                     raw_elevations)

    #shutil.copy2(os.path.join(DataFilesDir, 'polygons', BoundingPolygon), polygons)
    bounding_polygon_file = open(os.path.join(polygons, 'bounding_polygon.csv'), 'w')
    for coord in project_geom.coords[0]:
        bounding_polygon_file.write('%d,%d\n' % (coord[0], coord[1]))
    bounding_polygon_file.close()

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
    run_tsudat.run_tsudat(json_file)

    # remove temporary files
    #os.remove(json_file)
    
    return True
