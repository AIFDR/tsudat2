import os, sys
import logging
import shutil
import simplejson as json
import tempfile
from time import gmtime, strftime, sleep

from django import db
from django.contrib.auth.models import User
from django.conf import settings

from owslib.wcs import WebCoverageService

from tsudat.models import *
from celery.decorators import task
from geonode.maps.models import *

#import gdal
#from gdalconst import *
#import osr

from util.LatLongUTMconversion import LLtoUTM 
#from run_tsudat import run_tsudat

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
    TsuDATMux = settings.TSUDAT_MUX_DIR
    DataFilesDir = '%s/fake_ui_files.%s' % ('/home/software/tsudat2/run_tsudat', scenario.project.name)
    print DataFilesDir

    # create the user working directory
    #(run_dir, raw_elevations, boundaries, meshes,
            # polygons, gauges) = run_tsudat.make_tsudat_dir(TsuDATBase, user.username, scenario.project.name,
                    #                                        scenario.name, scenario.model_setup, scenario.event.tsudat_id)

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

    project_geom.transform(srid) 

    # Polygons
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

    # Raw Elevation Files
    RawElevationFiles = []

    wcs_url = settings.GEOSERVER_BASE_URL + 'wcs'

    '''
    wcs = WebCoverageService(wcs_url, version='1.0.0')
    pds = ProjectDataSet.objects.filter(project=scenario.project).order_by('ranking')
    output_format = "AAIGrid"
    driver = gdal.GetDriverByName(output_format)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(srid)
    dst_wkt = srs.ExportToPrettyWkt()
    eResampleAlg = None
    create_options = None
    for ds in pds:
        layer = Layer.objects.using('geonode').get(uuid=ds.dataset.geonode_layer_uuid)
        metadata = wcs.contents[layer.name]
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
        cmd = "/usr/bin/gdalwarp -t_srs EPSG:%d %s %s.tmp" % (srid, tif_file_path, tif_file_path)
        os.system(cmd)
        # Convert to AAIGrid
        cmd = "/usr/bin/gdal_translate -of %s %s.tmp %s" % (output_format, tif_file_path, asc_file_path)
        os.system(cmd)
        # Remove Intermediate files
        #os.remove(tif_file_path)
        #os.remove(tif_file_path + ".tmp")
        
        RawElevationFiles.append(asc_file_path)
    '''
    '''
        src_ds = gdal.Open( str(tif_file_path), GA_ReadOnly )
        dst_ds_tmp = driver.CreateCopy( str(asc_file_name + '.tmp'), src_ds, 0)
        dst_ds = driver.Create( str(asc_file_path), dst_ds_tmp.RasterXSize, dst_ds_tmp.RasterYSize)
        gdal.ReprojectImage(src_ds, dst_ds, None, dst_wkt)
        dst_ds = None
        dst_ds_tmp = None
        src_ds = None
    '''

    # Boundaries TODO
    LandwardBoundary = 'landward_boundary.csv'
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', LandwardBoundary), boundaries)
    UrsOrder = 'urs_order.csv'
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', UrsOrder), boundaries)
    STSFile = '%s.sts' % scenario.project.name
    shutil.copy2(os.path.join(DataFilesDir, 'boundaries', STSFile), boundaries)
    
    # Gauges
    gauge_file = open(os.path.join(gauges, 'gauges.csv'), 'w')
    gauge_file.write('easting,northing,name,elevation\n')
    gauge_points = GaugePoint.objects.filter(project=scenario.project)
    for gauge in gauge_points:
        gauge_geom = gauge.geom
        gauge_geom.transform(srid)
        gauge_file.write('%f,%f,%s,%f\n' % (gauge_geom.coords[0], gauge_geom.coords[1], gauge.name, 0.0))
    gauge_file.close()
    
    # Topographies TODO
    MeshFile = 'meshes.msh'
    Elevation = 'combined_elevation.pts'

    # pre-generated combined elevation data file
    topo = os.path.join(os.path.dirname(gauges), 'topographies')
    shutil.copy2(os.path.join(DataFilesDir, 'topographies', Elevation), topo)

    scenario_layers = scenario.output_layers.all()
    layers = []
    for layer in scenario_layers:
        layers.append(layer.name)

    # build the scenario json data file
    date_time = strftime("%Y%m%d%H%M%S", gmtime()) 
    json_file = os.path.join(run_dir, '%s.%s.%s.json' % (scenario.project.name, scenario.name, date_time))
               
    json_dict = {'working_directory': TsuDATBase,
                 'mux_directory': TsuDATMux,
                 'user': user.username,
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
                 'raster_resolution': scenario.raster_resolution,
                 'layers': layers, 
                 'area': ['All'], #TODO?
                 'get_results_max': True,
                 'get_timeseries': True,
                 'gauges': gauge_file.name,
                 'meshfile': MeshFile,
                 'interior_regions_data': InteriorRegions,
                 'bounding_polygon_maxarea': scenario.project.max_area,
                 'urs_order': UrsOrder,
                 'landward_boundary': LandwardBoundary,
                 'ascii_grid_filenames': [],
                 'zone': utm_zone,
                 'xminAOI': project_geom.extent[0],
                 'yminAOI': project_geom.extent[1],
                 'xmaxAOI': project_geom.extent[2],
                 'ymaxAOI': project_geom.extent[3],
                 'force_run': False, # if True, *forces* a simulation
                 'debug': True}	# if True, forces DEBUG logging
    with open(json_file, 'w') as fd:
        json.dump(json_dict, fd, indent=2, separators=(',', ':'))

    # now run the simulation
    #run_tsudat.run_tsudat(json_file)

    # Setup the new layers in the GeoNode

    # Create a project Map in the GeoNode 
    
    # Notify the User their job is finished

    return True
