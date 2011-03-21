import os, sys
import logging
import shutil
import simplejson as json
import tempfile
from time import gmtime, strftime

from django import db
from django.contrib.auth.models import User
from django.conf import settings

from tsudat.models import *
from celery.decorators import task

from util.LatLongUTMconversion import LLtoUTM 
from run_tsudat import run_tsudat

try:
    from notification import models as notification
except ImportError:
    notification = None

logger = logging.getLogger("tsudat2.tsudat.tasks")

@task
def run_tsudat_simulation(user, scenario_id):
    # Get the scenario object from the Database
    scenario = Scenario.objects.get(id=scenario_id)
        
    # the base of the TsuDAT user directory structures from settings.py 
    TsuDATBase = settings.TSUDAT_BASE_DIR
    DataFilesDir = '%s/fake_ui_files.%s' % (TsuDATBase, scenario.name)

    # create the user working directory
    (run_dir, raw_elevations, boundaries, meshes,
     polygons, gauges) = run_tsudat.make_tsudat_dir(TsuDATBase, user.username, scenario.project.name,
                                                    scenario.name, scenario.model_setup, scenario.event.tsudat_id)

    # Polygons
    
    project_geom = scenario.project.geom
    centroid = project_geom.centroid

    # This somewhat naively that the whole bounding polygon is in the same zone
    (UTMZone, UTMEasting, UTMNorthing) = LLtoUTM(23, centroid.coords[1], centroid.coords[0])
    if(len(UTMZone) == 3):
        utm_zone = int(UTMZone[0:2])
    else:
        utm_zone = int(UTMZone[0:1])
    if(centroid.coords[1] > 0):
        srid_base = 32600
    else:
        srid_base = 32700
    srid = srid_base + utm_zone
    print utm_zone, srid

    project_geom = scenario.project.geom
    project_geom.transform(srid) 

    bounding_polygon_file = open(os.path.join(polygons, 'bounding_polygon.csv'), 'w')
    for coord in project_geom.coords[0]:
        bounding_polygon_file.write('%f,%f\n' % (coord[0], coord[1]))
    bounding_polygon_file.close()
  
    internal_polygons = InternalPolygon.objects.filter(project=scenario.project).order_by('value')
    count = 0
    InteriorRegions = []
    for ip in internal_polygons:
        ipfile = open(os.path.join(polygons, 'ip%s.csv' % count), 'w')
        geom = ip.geom
        geom.transform(srid)
        for coord in geom.coords[0]:
            ipfile.write('%f,%f\n' % (coord[0], coord[1]))
        InteriorRegions.append([ipfile.name, ip.value])
        ipfile.close()
        geom = ipfile = None
        count += 1

    # Raw Elevation Files TODO
    RawElevationFiles = []

    for f in RawElevationFiles:
        shutil.copy2(os.path.join(DataFilesDir, 'raw_elevations', f),
                     raw_elevations)

    # Boundaries TODO
    LandwardBoundary = 'landward_boundary.csv'
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', LandwardBoundary), boundaries)
    UrsOrder = 'urs_order.csv'
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', UrsOrder), boundaries)
    STSFile = '%s.sts' % scenario.name
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', STSFile), boundaries)
    
    # Gauges
    gauge_file = open(os.path.join(gauges, 'gauges.csv'), 'w')
    gauge_file.write('easting,northing,name,elevation\n')
    gauge_points = GaugePoint.objects.filter(project=scenario.project)
    for gauge in gauge_points:
        gauge_geom = gauge.geom
        gauge_geom.transform(srid)
        gauge_file.write('%f,%f,%s,%f\n' % (gauge_geom.coords[0], gauge_geom.coords[1], gauge.name, 0.0)) #TODO Add Elevation to GP?
    gauge_file.close()
    
    # Topographies TODO
    MeshFile = 'meshes.msh'
    Elevation = 'combined_elevation.pts'

    # pre-generated combined elevation data file
    topo = os.path.join(os.path.dirname(gauges), 'topographies')
    shutil.copy2(os.path.join(DataFilesDir, 'topographies', Elevation), topo)

    # build the scenario json data file
    date_time = strftime("%Y%m%d%H%M%S", gmtime()) 
    json_file = os.path.join(run_dir, '%s.%s.%s.json' % (scenario.name, scenario.project.name, date_time))
               
    json_dict = {'user': user.username,
                 'project': scenario.project.name,
                 'scenario_name': scenario.name,
                 'setup': scenario.model_setup,
                 'event': scenario.event.tsudat_id,
                 'tide': scenario.initial_tidal_stage,
                 'start_time': scenario.start_time,
                 'end_time': scenario.end_time,
                 'smoothing': scenario.smoothing_param,
                 'bounding_polygon': bounding_polygon_file.name,
                 'elevation_data': RawElevationFiles,
                 'mesh_friction': scenario.default_friction_value,
                 'raster_resolution': 250, #TODO
                 'layers': ['stage', 'depth'], #TODO
                 'area': ['All'], #TODO?
                 'get_results_max': True,
                 'get_timeseries': True,
                 'gauges': gauge_file.name,
                 'meshfile': MeshFile,
                 'interior_regions_data': InteriorRegions,
                 'bounding_polygon_maxarea': 100000, #TODO
                 'urs_order': UrsOrder,
                 'landward_boundary': LandwardBoundary,
                 'ascii_grid_filenames': [],
                 'zone': utm_zone,
                 'xminAOI': project_geom.extent[0],
                 'xmaxAOI': project_geom.extent[1],
                 'yminAOI': project_geom.extent[2],
                 'ymaxAOI': project_geom.extent[3],
                 'force_run': False, # if True, *forces* a simulation
                 'debug': True}	# if True, forces DEBUG logging
    with open(json_file, 'w') as fd:
        json.dump(json_dict, fd, indent=2, separators=(',', ':'))

    # now run the simulation
    run_tsudat.run_tsudat(json_file)

    # Setup the new layers in the GeoNode

    # Create a project Map in the GeoNode 
    
    # Notify the User their job is finished

    return True
