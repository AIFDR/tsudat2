#!/usr/bin/env python

"""
Run an ANUGA simulation on an Amazon EC2 instance.

This module is called by the bootstrap code after all data has been loaded
from S3 and the environment set up.
"""

import sys
import os
import re
import shutil
import glob
import time
import json
import traceback
from Scientific.IO.NetCDF import NetCDFFile
import numpy as num
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

import anuga
from anuga.geometry.polygon import number_mesh_triangles
import anuga.utilities.log as log
import export_depthonland_max as edm
import export_newstage_max as enm

log.console_logging_level = log.CRITICAL+1    # turn console logging off
log.log_logging_level = log.DEBUG


# logger callback function
Logger = None


# where the generated files are gathered
OutputGenDir = '/tmp/tsudat_gen'

# define a 'project' object
class Project(object):
    pass

project = Project()

# populate with some fixed values
project.multi_mux = True


def run_model():
    """Run a tsunami simulation for a scenario."""

    # Read in boundary from ordered sts file
    event_sts = anuga.create_sts_boundary(project.event_sts)

    # Reading the landward defined points, this incorporates the original
    # clipping polygon minus the 100m contour
    landward_boundary = anuga.read_polygon(project.landward_boundary_file)

    # Combine sts polyline with landward points
    bounding_polygon_sts = event_sts + landward_boundary

    # Number of boundary segments
    num_ocean_segments = len(event_sts) - 1
    # Number of landward_boundary points
    num_land_points = anuga.file_length(project.landward_boundary_file)

    # Boundary tags refer to project.landward_boundary_file
    # 4 points equals 5 segments start at N
    boundary_tags={'back': range(num_ocean_segments+1,
                                 num_ocean_segments+num_land_points),
                   'side': [num_ocean_segments,
                            num_ocean_segments+num_land_points],
                   'ocean': range(num_ocean_segments)}

    # Build mesh and domain
    log.debug('bounding_polygon_sts=%s' % str(bounding_polygon_sts))
    log.debug('boundary_tags=%s' % str(boundary_tags))
    log.debug('project.bounding_maxarea=%s' % str(project.bounding_maxarea))
    log.debug('project.interior_regions=%s' % str(project.interior_regions))
    log.debug('project.mesh_file=%s' % str(project.mesh_file))

    domain = anuga.create_domain_from_regions(bounding_polygon_sts,
                                boundary_tags=boundary_tags,
                                maximum_triangle_area=project.bounding_maxarea,
                                interior_regions=project.interior_regions,
                                mesh_filename=project.mesh_file,
                                use_cache=False,
                                verbose=False)

    domain.geo_reference.zone = project.zone_number
    log.info('\n%s' % domain.statistics())

    domain.set_name(project.scenario)
    domain.set_datadir(project.output_folder)
    domain.set_minimum_storable_height(0.01)  # Don't store depth less than 1cm

    # set friction in interior regions, if any defined
    friction_list = []
    for (irtype, filename, friction) in project.interior_regions_list:
        if irtype.lower() == 'friction':
            friction_list.append([filename, friction])
    if friction_list:
        log.debug('friction_list=%s' % str(friction_list))
        poly_friction = []
        for (fname, friction) in friction_list:
            full_fname = os.path.join(project.polygons_folder, fname)
            log.debug('Reading friction polygon: %s' % full_fname)
            poly = anuga.read_polygon(full_fname)
            poly_friction.append((poly, friction))
            log.debug('poly=%s' % str(poly))
        domain.set_quantity('friction',
                            anuga.Polygon_function(poly_friction,
                                                   default=project.friction,
                                                   geo_reference=domain.geo_reference))

    # Set the initial stage in the offcoast region only
    if project.land_initial_conditions:
        IC = anuga.Polygon_function(project.land_initial_conditions,
                                    default=project.initial_tide,
                                    geo_reference=domain.geo_reference)
    else:
        IC = project.initial_tide

    domain.set_quantity('stage', IC, use_cache=True, verbose=False)
    domain.set_quantity('friction', project.friction)
    domain.set_quantity('elevation',
                        filename=project.combined_elevation_file,
                        use_cache=True, verbose=False, alpha=project.alpha)

    # Setup boundary conditions
    log.debug('Set boundary - available tags: %s' % domain.get_boundary_tags())

    Br = anuga.Reflective_boundary(domain)
    Bt = anuga.Transmissive_stage_zero_momentum_boundary(domain)
    Bd = anuga.Dirichlet_boundary([project.initial_tide, 0, 0])
    Bf = anuga.Field_boundary(project.event_sts+'.sts',
                        domain, mean_stage=project.initial_tide, time_thinning=1,
                        default_boundary=anuga.Dirichlet_boundary([0, 0, 0]),
                        boundary_polygon=bounding_polygon_sts,
                        use_cache=True, verbose=False)

    domain.set_boundary({'back': Br,
                         'side': Bt,
                         'ocean': Bf})

    # Evolve system through time
    t0 = time.time()
    for t in domain.evolve(yieldstep=project.yieldstep,
                           finaltime=project.finaltime,
                           skip_initial_step=False):
        if Logger:
            Logger(domain.timestepping_statistics())
        log.info('\n%s' % domain.timestepping_statistics())
        log.info('\n%s' % domain.boundary_statistics(tags='ocean'))

    log.info('Simulation took %.2f seconds' % (time.time()-t0))


def adorn_project(json_data):
    """Adorn the project object with data from the json file.

    json_data  path to the UI JSON data file
    """

    # parse the JSON
    with open(json_data, 'r') as fp:
        ui_dict = json.load(fp)

    # adorn project object with entries from ui_dict
    for (key, value) in ui_dict.iteritems():
        # convert to str (ANUGA can't handle unicode yet)
        key = str(key)
        if isinstance(value, basestring):
            value = str(value)

        # set new attribute in project object
        project.__setattr__(key, value)

    # if project.debug isn't defined, set it to False
    try:
        project.debug
    except AttributeError:
        project.debug = False

    # if .force_run isn't defined, set it to True
    try:
        project.force_run
    except AttributeError:
        project.force_run = True


def get_youngest_input():
    """Get date/time of youngest input file."""

    input_dirs = [project.polygons_folder, project.raw_elevation_folder]
    input_files = [project.urs_order_file,
                   os.path.join(project.boundaries_folder,
                                '%s.sts' % project.sts_filestem),
                   project.landward_boundary_file]

    youngest = 0.0	# time at epoch start

    # check all files in given directories
    for d in input_dirs:
        with os.popen('ls -l %s' % d) as fd:
            lines = fd.readlines()

        for fname in glob.glob(os.path.join(d, '*')):
            mtime = os.path.getmtime(fname)
            youngest = max(mtime, youngest)

    # check individual files
    for fname in input_files:
        mtime = os.path.getmtime(fname)
        youngest = max(mtime, youngest)

    return youngest


def export_results_max():
    """Export maximum results.

    Returns a list of generated files.
    """

    # initialise the list of generated files
    gen_files = []

    ######
    # Define allowed variable names and associated equations to generate values.
    ######
    # Note that mannings n (friction value) is taken as 0.01, as in the model
    # run density of water is 1000
    var_equations = {'stage': enm.export_newstage_max,
                     'oldstage': 'stage',
                     'momentum': '(xmomentum**2 + ymomentum**2)**0.5',
                     'olddepth': 'oldstage-elevation',
                     'depth': edm.export_depthonland_max,
                     'speed': '(xmomentum**2 + ymomentum**2)**0.5/(stage-elevation+1.e-6)',
                     'energy': '(((xmomentum/(stage-elevation+1.e-6))**2'
                               '  + (ymomentum/(stage-elevation+1.e-6))**2)'
                               '*0.5*1000*(stage-elevation+1.e-6))+(9.81*stage*1000)',
                     'bed_shear_stress': ('(((1/(stage-elevation+1.e-6)**(7./3.))*1000*9.81*0.01**2*(xmomentum/(stage-elevation+1.e-6))*((xmomentum/(stage-elevation+1.e-6))**2+(ymomentum/(stage-elevation+1.e-6))**2)**0.5)**2'
                                          '+ ((1/(stage-elevation+1.e-6)**(7./3.))*1000*9.81*0.01**2*(ymomentum/(stage-elevation+1.e-6))*((xmomentum/(stage-elevation+1.e-6))**2+(ymomentum/(stage-elevation+1.e-6))**2)**0.5)**2)**0.5'),
                     'elevation': 'elevation'}

    ######
    # Start script, running through variables, area, sww file
    ######

    for which_var in project.layers_list:
        which_var = which_var.lower()
        log.info("Exporting value: %s" % which_var)

        if which_var not in var_equations:
            log.critical('Unrecognized variable name: %s' % which_var)
            break

        project.export_area = project.export_area.lower()
        if project.export_area == 'all':
            easting_min = None
            easting_max = None
            northing_min = None
            northing_max = None
        elif project.export_area == 'aoi':
                easting_min = project.xminAOI
                easting_max = project.xmaxAOI
                northing_min = project.yminAOI
                northing_max = project.ymaxAOI
        else:
            log.critical('Unrecognized area name: %s' % project.export_area)
            break

        name = os.path.join(project.output_folder, project.scenario)

        outname = name + '_' + project.export_area + '_' + which_var
        quantityname = var_equations[which_var]

        log.info('Generating output file: %s' % (outname+'.asc'))

        # assume 'quantityname' is a string, handle in the old way,
        #  else call the handler function (same params as anuga.sww2dem)
        if isinstance(quantityname, basestring):
            export_func = anuga.sww2dem
        elif callable(quantityname):
            export_func = quantityname

        export_func(name+'.sww', outname+'.asc', quantity=quantityname,
                    reduction=max, cellsize=project.cell_size,
                    easting_min=easting_min, easting_max=easting_max,
                    northing_min=northing_min, northing_max=northing_max,
                    verbose=False)

        # add generated filename to result list
        gen_files.append(outname+'.asc')

    return gen_files


def get_timeseries():
    """Get time series data"

    Returns a list of generated files.
    """

    # generate the result files
    name = os.path.join(project.output_folder, project.scenario+'.sww')
    log.debug('get_timeseries: input SWW file=%s' % name)
    log.debug('get_timeseries: gauge file=%s' % project.gauge_file)
    anuga.sww2csv_gauges(name, project.gauge_file, quantities=project.layers_list,
                         verbose=False)

    # since ANUGA code doesn't return a list of generated files,
    # look in output directory for 'gauge_*.csv' files.
    glob_mask = os.path.join(project.output_folder, 'gauge_*.csv')
    return glob.glob(glob_mask)


def make_stage_plot(filename, out_dir=None):
    """Make a stage graph from a timeseries file.

    filename  path to the timeseries file
    out_dir   directory to put plot file in
              (if not supplied, use same directory as input file)

    Creates a PNG timeseries plot file from the timeseries file.

    Assumes the input file is CSV format, 1 header line and columns:
        time, hours, stage, depth
    """

    # read timeseries file, get data
    with open(filename) as fp:
        lines = fp.readlines()

    # skip 1 header line
    lines = lines[1:]

    # convert CSV lines into X (hours) and Y (stage) data arrays
    hours = []
    stage = []
    for line in lines:
        (_, hval, sval, _) = line.strip().split(',')
        hours.append(float(hval))
        stage.append(float(sval))

    # get gauge filename and create matching PNG name
    data_filename = os.path.basename(filename)
    data_dir = os.path.dirname(filename)
    (stem, _) = data_filename.rsplit('.', 1)
    picname = stem + '.png'

    if out_dir is None:
        out_dir = data_dir

    picname = os.path.join(out_dir, picname)

    # get gauge name from filename
    (_, gaugename) = stem.rsplit('_', 1)

    # plot the graph
    fpath = '/usr/share/fonts/truetype/ttf-liberation/LiberationSans-Regular.ttf'
    prop = fm.FontProperties(fname=fpath)

    fig = plt.figure()
    ax = fig.add_subplot(111, axisbg='#f0f0f0')
    ax.plot(hours, stage)
    ax.grid(True)
    xticks = ax.xaxis.get_major_ticks()
    yticks = ax.yaxis.get_major_ticks()
    for xytext in xticks + yticks:
        xytext.label1.set_fontproperties(prop)
    ax.set_xlabel('time (hours)', fontproperties=prop)
    ax.set_ylabel('stage (m)', fontproperties=prop)
    ax.set_title("Stage at gauge '%s'" % gaugename, fontproperties=prop)
    ax.title.set_fontsize(14)

    plt.savefig(picname)

    return picname


def run_tsudat(json_data, logger=None):
    """Run ANUGA using data from a JSON data file.

    json_data  the path to the JSON data file

    Returns a dictionary of {'<type of file>': <list of files>, ...}.
    The dictionary keys and values addd here are:
        'log':              list of a single path to the log file
        'results_max':      list of ASC files containing maximum values
        'sww':              list of all SWW files produced
        'timeseries':       list of all gauge files produced
        'timeseries_plot':  list of all plots for gauge files produced

    For example:
    {'log': ['/tmp/tsudat/user/project/VictorHarbour/trial/outputs/tsudat.log'],
     'results_max': ['/tmp/tsudat/user/project/VictorHarbour/trial/outputs/VictorHarbour_all_stage.asc',
                     '/tmp/tsudat/user/project/VictorHarbour/trial/outputs/VictorHarbour_all_depth.asc'],
     'sww': ['/tmp/tsudat/user/project/VictorHarbour/trial/outputs/VictorHarbour.sww'],
     'timeseries': ['/tmp/tsudat/user/project/VictorHarbour/trial/outputs/gauge_inner4.csv',
                    '/tmp/tsudat/user/project/VictorHarbour/trial/outputs/gauge_inner1.csv',
                    '/tmp/tsudat/user/project/VictorHarbour/trial/outputs/gauge_inner3.csv']}
    """


    def dump_project_py():
        """Debug routine - dump project attributes to the log."""

        # list all project.* attributes
        for key in dir(project):
            if not key.startswith('__'):
                try:
                    log.info('project.%s=%s' % (key, eval('project.%s' % key)))
                except AttributeError:
                    pass

    # set global logger
    global Logger
    Logger = logger

    # get JSON data and adorn project object with its data
    adorn_project(json_data)

    if project.debug:
        dump_project_py()

    # run the tsudat simulation
    youngest_input = get_youngest_input()
    sww_file = os.path.join(project.output_folder, project.scenario+'.sww')
    try:
        sww_ctime = os.path.getctime(sww_file)
    except OSError:
        sww_ctime = 0.0		# SWW file not there

    if project.force_run or youngest_input > sww_ctime:
        log.info('#'*90)
        log.info('# Running simulation')
        log.info('#'*90)
        if Logger:
            Logger('Running simulation')
        run_model()
        log.info('End of simulation')
        if Logger:
            Logger('End of simulation')
    else:
        log.info('#'*90)
        log.info('# Not running simulation')
        log.info('# If you want to force a simulation run, select FORCE RUN')
        log.info('#'*90)
        if Logger:
            Logger('Not running simulation\n'
                   'If you want to force a simulation run, select FORCE RUN')


    # add *all* SWW files in the output directory to result dictionary
    # (whether we ran a simulation or not)
    glob_mask = os.path.join(project.output_folder, '*.sww')
    project.payload['sww'] = glob.glob(glob_mask)

    # now do optional post-run extractions
    if project.get_results_max:
        log.info('~'*90)
        log.info('~ Running export_results_max()')
        log.info('~'*90)
        file_list = export_results_max()
        if Logger:
            Logger('Running export_results_max()')
        project.payload['results_max'] = file_list  # add files to output dict
        log.info('export_results_max() has finished')
        if Logger:
            Logger('export_results_max() has finished')
    else:
        log.info('~'*90)
        log.info('~ Not running export_results_max() - not requested')
        log.info('~'*90)
        if Logger:
            Logger('Not running export_results_max() - not requested')

    if project.get_timeseries:
        log.info('~'*90)
        log.info('~ Running get_timeseries()')
        log.info('~'*90)
        if Logger:
            Logger('Running get_timeseries()')
        file_list = get_timeseries()
        project.payload['timeseries'] = file_list  # add files to output dict
        # generate plot files
        plot_list = []
        for filename in file_list:
            plot_file = make_stage_plot(filename)
            plot_list.append(plot_file)
        project.payload['timeseries_plot'] = plot_list  # add files to output dict

        log.info('get_timeseries() has finished')
        if Logger:
            Logger('get_timeseries() has finished')
    else:
        log.info('~'*90)
        log.info('~ Not running get_timeseries() - not requested')
        log.info('~'*90)
        if Logger:
            Logger('Not running get_timeseries() - not requested')

    return project.payload
