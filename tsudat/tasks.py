import os, sys
import logging
import shutil
import simplejson as json
import tempfile
import datetime
from datetime import timedelta
from time import gmtime, strftime, sleep

from django import db
from django.contrib.auth.models import User
from django.conf import settings

from owslib.wcs import WebCoverageService

from tsudat import landward
from tsudat.utils import process_finished_simulation
from tsudat.models import *
from tsudat.build_urs_boundary import build_boundary_deformation

from celery.task.schedules import crontab
from celery.decorators import task, periodic_task

from geonode.maps.models import *
from geonode.maps.utils import *
from geonode.maps.views import *

from osgeo import gdal
#from gdalconst import *
from osgeo import osr

from util.LatLongUTMconversion import LLtoUTM 

from run_tsudat import run_tsudat_ncios as run_tsudat
#from run_tsudat import run_tsudat_local as run_tsudat
from run_tsudat import messaging_amqp

import re

try:
    from notification import models as notification
except ImportError:
    notification = None

logger = logging.getLogger("tsudat2.tsudat.tasks")

# Move somewhere more accessible
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def _slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    From Django's "django/template/defaultfilters.py".
    """
    import unicodedata
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


def run_create_sim_boundary(user, project_id):
    """
    Create  sts and csv files for the user, based on the event
    that they selected and the polygon they drew.
    
    """
    # This function should be focused on getting the database info out
    # and passing it on.

    # Get the scenario object from the Database
    scenario = Scenario.objects.get(id=scenario_id)
    
    # the base of the TsuDAT user directory structures from settings.py 
    TsuDATBase = settings.TSUDAT_BASE_DIR # '/data/run_tsudat/'
    TsuDATMux = settings.TSUDAT_MUX_DIR # '/data/Tsu-DAT_Data/earthquake_data'

    #actual_setup - remove this variable
    
    # QU Do we need this?
    # can scenario.project.name be None?
    # fake a project name                                  ##?
    if not scenario.project.name:                         ##?
        scenario.project.name = _slugify(scenario.name)   ##?
        # scenario.project.save() Needed?
        
                
    # create the user working directory
    (work_dir, raw_elevations, boundaries, meshes, polygons, gauges,
     topographies, user_dir) = run_tsudat.make_tsudat_dir(
        TsuDATBase, user.username,
        _slugify(scenario.project.name),
        _slugify(scenario.name),
        actual_setup,
        scenario.event.tsudat_id)
     # Later these directories will be written to.

    project_geom = scenario.project.geom
    project_extent = scenario.project.geom.extent
    centroid = project_geom.centroid
    
    
    # This somewhat naively assumes that the whole bounding polygon is
    # in the same zone
    (UTMZone, UTMEasting, UTMNorthing) = LLtoUTM(23, centroid.coords[1],
                                                 centroid.coords[0])
    if(len(UTMZone) == 3):
        utm_zone = int(UTMZone[0:2])
    else:
        utm_zone = int(UTMZone[0:1])
    if(centroid.coords[1] > 0):
        srid_base = 32600
    else:
        srid_base = 32700
    srid = srid_base + utm_zone
    scenario.project.srid = srid # QU why add to the data base?
    scenario.project.save()

    project_geom.transform(srid) # QU what does this do? update DB?
    
    # DSG - check how the polygon info gets to the boundary maker
    # Polygons
    #  Write out the bounding_polygon.csv to a file
    print polygons
    bounding_polygon_file = open(os.path.join(
            polygons, 'bounding_polygon.csv'), 'w')
    for coord in project_geom.coords[0][:-1]:
        bounding_polygon_file.write('%f,%f\n' % (coord[0], coord[1]))
    bounding_polygon_file.close()
    
    # skipping Internal Polygons
    # skipping Raw Elevation Files
    print " Getting here"

    # Landward Boundary 
    #Iterate over the in the project geometry and
    # add a l or s flag and call landward.landward with them
    points_list = []
    for coord in project_geom.coords[0][:-1]:
        pnt_wkt = 'SRID=%s;POINT(%f %f)' % (srid, coord[0], coord[1])
        print "srid", srid
        print "coord",coord
        #print "",
        land = Land.objects.filter(wkb_geometry__intersects=pnt_wkt)
        if(land.count() > 0):
            points_list.append((coord[0], coord[1], "l")) 
        else:
            points_list.append((coord[0], coord[1], "s")) 
    print('points_list=%s' % str(points_list))
    landward_points = landward.landward(points_list)
    print('landward_points=%s' % str(landward_points))
    
    # Write out the landward points to a file
    landward_boundary_file = open(os.path.join(boundaries, 'landward_boundary.csv'), 'w')
    for pt in landward_points:
        landward_boundary_file.write('%f,%f\n' % (pt[0], pt[1]))
    landward_boundary_file.close()

    # Write out the Interior Hazard Points File
    interior_hazard_points_file = open(os.path.join(boundaries, 
                                                    'interior_hazard_points.csv'), 'w')
    hps = HazardPoint.objects.filter(geom__intersects=project_geom).order_by('tsudat_id')
    for hp in hps:
        the_geom = hp.geom
        latitude=the_geom.coords[1]
        longitude=the_geom.coords[0]
        the_geom.transform(srid)
        interior_hazard_points_file.write('%d,%f,%f,%f,%f\n' % (
                hp.tsudat_id,longitude,latitude,the_geom.coords[0], the_geom.coords[1]))
    interior_hazard_points_file.close()
    
     # Skipping Gauges
     # Skipping Layers 
    
    # build the simulation boundary json data file
    date_time = strftime("%Y%m%d%H%M%S", gmtime()) 
    json_file = os.path.join(work_dir, '%s.%s.json' % (_slugify(scenario.name), 
                                                       date_time))

    json_dict_sim_boundary = {
        'user': user.username,
        'user_directory': user_dir,
        'project': _slugify(scenario.project.name),
        'project_id': scenario.project.id,
        'scenario': _slugify(scenario.name),
        'scenario_id': scenario.id,
        'event_number': scenario.event.tsudat_id,
        'working_directory': TsuDATBase,
        'mux_directory': TsuDATMux,
        'initial_tide': scenario.initial_tidal_stage,
        'start_time': scenario.start_time,
        'end_time': scenario.end_time,
        'bounding_polygon_file': bounding_polygon_file.name,
        'interior_hazard_points_file': interior_hazard_points_file.name, 
        'landward_boundary_file': landward_boundary_file.name,
        'zone_number': utm_zone,
        #'setup': actual_setup,
        #'smoothing': scenario.smoothing_param,
        #'raw_elevation_directory': raw_elevations,
        #'elevation_data_list': RawElevationFiles,
        #'mesh_friction': scenario.default_friction_value,
        #'raster_resolution': scenario.raster_resolution,
        #'export_area': "AOI" if scenario.use_aoi == True else "ALL",
        #'gauge_file': gauge_file.name,
        #'bounding_polygon_maxarea': scenario.project.max_area,
        #'interior_regions_list': InteriorRegions,
        #'layers_list': layers, 
        #'get_results_max': True,
        #'get_timeseries': True 
        }

    with open(json_file, 'w') as fd:
        json.dump(json_dict_sim_boundary, fd, indent=2, separators=(',', ':'))
        
    scenario.tsudat_payload = json.dumps(json_dict_sim_boundary) 
    scenario.save()
    
    # now run the simulation
    run_tsudat.run_tsudat(json_file)
    scenario.anuga_status = "QUEUE"
    scenario.save()
    return True
    
def create_internal_boundary_files(user, project_id, event_id):
    """
    Create bounding_polygon_file, interior_hazard_points_file and
    landward_boundary_file. Get info needed from the database.
    
    """
    # This function should be focused on getting the database info out
    # and passing it on.
    # Get the project  object from the Database
    
    project = Project.objects.get(id=project_id)
    
    # the base of the TsuDAT user directory structures from settings.py 
    TsuDATBase = settings.TSUDAT_BASE_DIR # '/data/run_tsudat/'

        
                
    # create the user working directory
    (work_dir, raw_elevations, boundaries, meshes, polygons, gauges,
     topographies, user_dir) = run_tsudat.make_tsudat_dir(
        TsuDATBase, user.username,
        'project_boundary',
        'scenario_boundary',
        'another_dir',
        event_id)
     # Later these directories will be written to.

    project_geom = project.geom
    project_extent = project.geom.extent
    centroid = project_geom.centroid
    
     # This somewhat naively assumes that the whole bounding polygon is
    # in the same zone
    (UTMZone, UTMEasting, UTMNorthing) = LLtoUTM(23, centroid.coords[1],
                                                 centroid.coords[0])
    if(len(UTMZone) == 3):
        utm_zone = int(UTMZone[0:2])
    else:
        utm_zone = int(UTMZone[0:1])
    if(centroid.coords[1] > 0):
        srid_base = 32600
    else:
        srid_base = 32700
    srid = srid_base + utm_zone
    
    project_geom.transform(srid) # QU what does this do? update DB?
    
    # DSG - check how the polygon info gets to the boundary maker
    # Polygons
    #  Write out the bounding_polygon.csv to a file
    print polygons
    bounding_polygon_file = open(os.path.join(
            polygons, 'bounding_polygon.csv'), 'w')
    for coord in project_geom.coords[0][:-1]:
        bounding_polygon_file.write('%f,%f\n' % (coord[0], coord[1]))
    bounding_polygon_file.close()
    
    # skipping Internal Polygons
    # skipping Raw Elevation Files
    
    # Landward Boundary 
    #Iterate over the in the project geometry and
    # add a l or s flag and call landward.landward with them
    points_list = []
    for coord in project_geom.coords[0][:-1]:
        pnt_wkt = 'SRID=%s;POINT(%f %f)' % (srid, coord[0], coord[1])
        land = Land.objects.filter(wkb_geometry__intersects=pnt_wkt)
        if(land.count() > 0):
            points_list.append((coord[0], coord[1], "l")) 
        else:
            points_list.append((coord[0], coord[1], "s")) 
    print('points_list=%s' % str(points_list))
    landward_points = landward.landward(points_list)
    print('landward_points=%s' % str(landward_points))
    
    # Write out the landward points to a file
    landward_boundary_file = open(os.path.join(boundaries, 'landward_boundary.csv'), 'w')
    for pt in landward_points:
        landward_boundary_file.write('%f,%f\n' % (pt[0], pt[1]))
    landward_boundary_file.close()

    # Write out the Interior Hazard Points File
    interior_hazard_points_file = open(os.path.join(boundaries, 
                                                    'interior_hazard_points.csv'), 'w')
    hps = HazardPoint.objects.filter(geom__intersects=project_geom).order_by('tsudat_id')
    for hp in hps:
        the_geom = hp.geom
        latitude=the_geom.coords[1]
        longitude=the_geom.coords[0]
        the_geom.transform(srid)
        interior_hazard_points_file.write('%d,%f,%f,%f,%f\n' % (
                hp.tsudat_id,longitude,latitude,the_geom.coords[0], the_geom.coords[1]))
    interior_hazard_points_file.close()
    
    
    # build the simulation boundary json data file
    date_time = strftime("%Y%m%d%H%M%S", gmtime()) 
    json_file = os.path.join(work_dir, '%s.%s.json' % (project_id, 
                                                       date_time))

    int_boundary_dic = {
        'user': user.username,
        'user_directory': user_dir,
        'project': _slugify(project.name),
        'project_id': project_id,
        'event_number': event_id,
        'working_directory': TsuDATBase,
        'bounding_polygon_file': bounding_polygon_file.name,
        'interior_hazard_points_file': interior_hazard_points_file.name, 
        'landward_boundary_file': landward_boundary_file.name,
        'zone_number': utm_zone
        }
    return int_boundary_dic



@task
def download_tsunami_waveform(user, data_list): 

    project_id = data_list[0]
    event_id = int(data_list[1])
    int_boundary_dic = create_internal_boundary_files(
        user, project_id, event_id)
    landward_boundary_path = int_boundary_dic['landward_boundary_file']
    interior_hazard_points_path = \
        int_boundary_dic['interior_hazard_points_file']
    mux_data_folder = settings.TSUDAT_MUX_DIR
    deformation_folder  = settings.TSUDAT_DEF_DIR
    # /data/run_tsudat/sts_and_deformation.zip
    zip_filename = os.path.join(
        int_boundary_dic['working_directory'],
        'sts_and_deformation.zip')
    build_boundary_deformation(landward_boundary_path, 
                               interior_hazard_points_path,
                               event_id, 
                               mux_data_folder, 
                               deformation_folder, 
                               zip_filename)
    print "yeah"
    return zip_filename

@task
def run_tsudat_simulation(user, scenario_id):
    #run_small(user, project_id)
    run_tsudat_simulation_func(user, scenario_id)


def download_scenario(user, scenario_id):
    """
    Generate a working directory for running ANUGA
    Create/Copy all of the files to that directory that are necessary
    for running the simulation. Generate a json run file and call run_tsudat.
    Notes here: https://github.com/AIFDR/tsudat2/wiki/Create-anuga-run-script
    """
    create_dir()
    # Get the scenario object from the Database
    scenario = Scenario.objects.get(id=scenario_id)
    
    # the base of the TsuDAT user directory structures from settings.py 
    TsuDATBase = settings.TSUDAT_BASE_DIR
    TsuDATMux = settings.TSUDAT_MUX_DIR

    # change setup value to one of expected strings
    print('original scenario.model_setup=%s' % scenario.model_setup)
    trial_edit = {'t': 'trial', 'T': 'trial', 'trial': 'trial', 'TRIAL': 'trial',
                  'f': 'final', 'F': 'final', 'final': 'final', 'FINAL': 'final'}
    actual_setup = trial_edit.get(scenario.model_setup, 'trial')
    print('actual_setup=%s' % actual_setup)

    # fake a prject name                                  ##?
    if not scenario.project.name:                         ##?
        scenario.project.name = _slugify(scenario.name)   ##?
               
    # create the user working directory
    (work_dir, raw_elevations, boundaries, meshes, polygons, gauges,
     topographies, user_dir) = run_tsudat.make_tsudat_dir(TsuDATBase, user.username,
                                                          _slugify(scenario.project.name),
                                                          _slugify(scenario.name),
##?                                                          scenario.model_setup,
                                                          actual_setup,
                                                          scenario.event.tsudat_id)

    project_geom = scenario.project.geom
    project_extent = scenario.project.geom.extent
    centroid = project_geom.centroid

    # This somewhat naively assumes that the whole bounding polygon is in the same zone
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
    scenario.project.srid = srid
    scenario.project.save()

    project_geom.transform(srid) 

    # Polygons
    print polygons
    bounding_polygon_file = open(os.path.join(polygons, 'bounding_polygon.csv'), 'w')
    for coord in project_geom.coords[0][:-1]:
        bounding_polygon_file.write('%f,%f\n' % (coord[0], coord[1]))
    bounding_polygon_file.close()
 
    # Internal Polygons 
    internal_polygons = InternalPolygon.objects.filter(project=scenario.project).order_by('value')
    count = 0
    InteriorRegions = []
    for ip in internal_polygons:
        ipfile = open(os.path.join(polygons, 'ip%s.csv' % count), 'w')
        geom = ip.geom
        geom.transform(srid)
        for coord in geom.coords[0][:-1]:
            ipfile.write('%f,%f\n' % (coord[0], coord[1]))
        if(ip.type == 1):
            type = "resolution"
        elif(ip.type == 2):
            type = "friction"
        elif(ip.type == 3):
            type = "aoi"
        InteriorRegions.append([type, ipfile.name, ip.value])
        ipfile.close()
        geom = ipfile = None
        count += 1

    # Raw Elevation Files
    RawElevationFiles = []
    elevation_files = []

    wcs_url = settings.GEOSERVER_BASE_URL + 'wcs'
    wcs = WebCoverageService(wcs_url, version='1.0.0')
    pds = ProjectDataSet.objects.filter(project=scenario.project).order_by('ranking')
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(srid)
    dst_wkt = srs.ExportToPrettyWkt()
    eResampleAlg = None
    create_options = None
    
    output_format = "AAIGrid"
    driver = gdal.GetDriverByName(output_format)
    
    for ds in pds:
        layer = Layer.objects.get(typename=ds.dataset.typename)
        elevation_files.append(layer.typename)
        logger.info(wcs.contents)
        metadata = wcs.contents[layer.typename]
        print metadata.grid
        resx = metadata.grid.offsetvectors[0][0]
        resy = abs(float(metadata.grid.offsetvectors[1][1]))
        formats = metadata.supportedFormats
        print formats
        cvg = wcs.getCoverage(identifier=layer.typename, 
                format='GeoTIFF', 
                crs="EPSG:4326", 
                bbox=(project_extent[0], 
                    project_extent[1], 
                    project_extent[2], 
                    project_extent[3]), 
                resx=resx, 
                resy=resy)
        # Need to make sure the ranking numbers are unique for each project (enforced with DB constraint?)
        tif_file_name = '%s.tif' % ds.ranking
        tif_file_path = os.path.join(raw_elevations, tif_file_name)
        asc_file_name = '%s.asc' % ds.ranking
        asc_file_path = os.path.join(raw_elevations, asc_file_name)
        out = open(tif_file_path, 'wb')
        out.write(cvg.read())
        out.close()
       
        # Warp to UTM
        cmd = "/usr/bin/gdalwarp -srcnodata -9999 -dstnodata -9999 -t_srs EPSG:%d %s %s.tmp" % (srid, tif_file_path, tif_file_path)
        os.system(cmd)
        # Convert to AAIGrid
        cmd = "/usr/bin/gdal_translate -a_nodata -9999 -of %s %s.tmp %s" % (output_format, tif_file_path, asc_file_path)
        os.system(cmd)
        # Remove Intermediate files
        #os.remove(tif_file_path)
        #os.remove(tif_file_path + ".tmp")
      
        # Rename the .prj file to .prj.wkt
        shutil.move(asc_file_path.replace('.asc', '.prj'), asc_file_path.replace('.asc', '.prj.wkt'))
         
        # Generate a prj.adf style prj file
        # NOTE: Not sure if this will work in all cases?
        prj_file_name = '%s.prj' % ds.ranking
        prj_file = open(os.path.join(raw_elevations, prj_file_name), 'w')
        prj_file.write('Projection    UTM\n')
        prj_file.write('Zone          %d\n' % utm_zone)
        prj_file.write('Datum         WGS1984\n')
        prj_file.write('Zunits        NO\n')
        prj_file.write('Units         METERS\n')
        prj_file.write('Spheroid      WGS_1984\n')
        prj_file.write('Xshift        500000\n')
        prj_file.write('Yshift        10000000\n')
        prj_file.write('Parameters\n')
        prj_file.write('NODATA_value  -9999')
        prj_file.close()        

        RawElevationFiles.append(asc_file_path)
         
        '''
        src_ds = gdal.Open( str(tif_file_path), GA_ReadOnly )
        dst_ds_tmp = driver.CreateCopy( str(asc_file_name + '.tmp'), src_ds, 0)
        dst_ds = driver.Create( str(asc_file_path), dst_ds_tmp.RasterXSize, dst_ds_tmp.RasterYSize)
        gdal.ReprojectImage(src_ds, dst_ds, None, dst_wkt)
        dst_ds = None
        dst_ds_tmp = None
        src_ds = None
        '''

    # Landward Boundary
    
    # Iterate over the in the project geometry and add a l or s flag and call landward.landward with them
    points_list = []
    for coord in project_geom.coords[0][:-1]:
        pnt_wkt = 'SRID=%s;POINT(%f %f)' % (srid, coord[0], coord[1])
        land = Land.objects.filter(the_geom__intersects=pnt_wkt)
        if(land.count() > 0):
            points_list.append((coord[0], coord[1], "l")) 
        else:
            points_list.append((coord[0], coord[1], "s")) 
    print('points_list=%s' % str(points_list))
    landward_points = landward.landward(points_list)
    print('landward_points=%s' % str(landward_points))
    
    # Write out the landward points to a file
    landward_boundary_file = open(os.path.join(boundaries, 'landward_boundary.csv'), 'w')
    for pt in landward_points:
        landward_boundary_file.write('%f,%f\n' % (pt[0], pt[1]))
    landward_boundary_file.close()

    # Interior Hazard Points File
    interior_hazard_points_file = open(os.path.join(boundaries, 'interior_hazard_points.csv'), 'w')
    hps = HazardPoint.objects.filter(geom__intersects=project_geom).order_by('tsudat_id')
    for hp in hps:
        the_geom = hp.geom
        latitude=the_geom.coords[1]
        longitude=the_geom.coords[0]
        the_geom.transform(srid)
        interior_hazard_points_file.write('%d,%f,%f,%f,%f\n' % (hp.tsudat_id,longitude,latitude,the_geom.coords[0], the_geom.coords[1]))
    interior_hazard_points_file.close()
    
    # Gauges
    gauge_file = open(os.path.join(gauges, 'gauges.csv'), 'w')
    gauge_file.write('easting,northing,name,elevation\n')
    gauge_points = GaugePoint.objects.filter(project=scenario.project)
    for gauge in gauge_points:
        gauge_geom = gauge.geom
        gauge_geom.transform(srid)
        gauge_file.write('%f,%f,%s,%f\n' % (gauge_geom.coords[0], gauge_geom.coords[1], gauge.name, 0.0))
    gauge_file.close()
   
    # Layers 
    scenario_layers = scenario.output_layers.all()
    layers = []
    for layer in scenario_layers:
        layers.append(layer.name)

    # build the scenario json data file
    date_time = strftime("%Y%m%d%H%M%S", gmtime()) 
    json_file = os.path.join(work_dir, '%s.%s.json' % (_slugify(scenario.name), date_time))

    json_dict = {
                    'user': user.username,
                    'user_directory': user_dir,
                    'project': _slugify(scenario.project.name),
                    'project_id': scenario.project.id,
                    'scenario': _slugify(scenario.name),
                    'scenario_id': scenario.id,
##?                    'setup': scenario.model_setup,
                    'setup': actual_setup,
                    'event_number': scenario.event.tsudat_id,
                    'working_directory': TsuDATBase,
                    'mux_directory': TsuDATMux,
                    'initial_tide': scenario.initial_tidal_stage,
                    'start_time': scenario.start_time,
                    'end_time': scenario.end_time,
                    'smoothing': scenario.smoothing_param,
                    'bounding_polygon_file': bounding_polygon_file.name,
                    'raw_elevation_directory': raw_elevations,
                    'elevation_data_list': RawElevationFiles,
                    'mesh_friction': scenario.default_friction_value,
                    'raster_resolution': scenario.raster_resolution,
                    'export_area': "AOI" if scenario.use_aoi == True else "ALL",
                    'gauge_file': gauge_file.name,
                    'bounding_polygon_maxarea': scenario.project.max_area,
                    'interior_regions_list': InteriorRegions,
                    'interior_hazard_points_file': interior_hazard_points_file.name, 
                    'landward_boundary_file': landward_boundary_file.name,
                    'zone_number': utm_zone,
                    'layers_list': layers, 
                    'get_results_max': True,
                    'get_timeseries': True 
                }

    with open(json_file, 'w') as fd:
        json.dump(json_dict, fd, indent=2, separators=(',', ':'))

    scenario.tsudat_payload = json.dumps(json_dict) 
    scenario.save()
    
    # now run the simulation
    run_tsudat.run_tsudat(json_file)
    scenario.anuga_status = "QUEUE"
    scenario.save()
    return True


@periodic_task(run_every=timedelta(seconds=15))
def process_anuga_message():
    print "firing process_anuga_message task" 

    c = messaging_amqp.ServerMessages()
    while True:
        msg = c.recv_message()
        if msg is None:
            break
        print('Server got message: %s' % msg)
        
        # Ack and delete the message
        c.ack_message()

        output_json = json.loads(msg)
        scenario = Scenario.objects.get(pk=output_json['scenario_id'])
        user = User.objects.get(username=output_json['user']) 

        if output_json['status'] == "START":
            scenario.anuga_status = output_json['status']
            scenario.anuga_instance = output_json['instance']
            scenario.anuga_start_timestamp = datetime.datetime.fromtimestamp(float(output_json['time']))
            scenario.save()
        elif output_json['status'] == "ABORT":
            scenario.anuga_status = output_json['status'] 
            scenario.anuga_abort_message = output_json['message']
            scenario.anuga_log_timestamp = datetime.datetime.fromtimestamp(float(output_json['time']))
            scenario.save()
        elif output_json['status'] == "LOG":
            scenario.anuga_status = output_json['status']
            scenario.anuga_log_message = output_json['msg']
            scenario.anuga_log_timestamp = datetime.datetime.fromtimestamp(float(output_json['time']))
            #scenario.save()
        elif output_json['status'] == "STOP" and "payload" in output_json.keys():
            scenario.anuga_payload = output_json["payload"]
            scenario.anuga_status = output_json['status']
            scenario.anuga_end_timestamp = datetime.datetime.fromtimestamp(float(output_json['time']))
            scenario.save()
            process_finished_simulation(scenario)
        elif output_json['status'] == "IDLE":
            pass
        
