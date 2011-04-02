"""
Run an ANUGA simulation on the Amazon EC2.
"""

import sys
import os
import re
import shutil
import glob
import time
import json
import traceback
import zipfile
import tempfile
import boto
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
log.log_logging_level = log.INFO


# the AMI we are going to run
DefaultAmi = 'ami-88c439e1'  # Ubuntu_10.04_TsuDAT_2.0.9
#DefaultAmi = 'ami-e4c4398d'  # Ubuntu_10.04_TsuDAT_2.0.8
#DefaultAmi = 'ami-00c43969'  # Ubuntu_10.04_TsuDAT_2.0.7
#DefaultAmi = 'ami-46d72a2f'  # Ubuntu_10.04_TsuDAT_2.0.6
#DefaultAmi = 'ami-b2d429db'  # Ubuntu_10.04_TsuDAT_2.0.5
#DefaultAmi = 'ami-08d42961'  # Ubuntu_10.04_TsuDAT_2.0.4
## BAD  DefaultAmi = 'ami-12da277b'  # Ubuntu_10.04_TsuDAT_2.0.3
#DefaultAmi = 'ami-54e71a3d'  # Ubuntu_10.04_TsuDAT_2.0.2

# the authentication stuff
AccessKey = 'AKIAIKGYJFXGT5TFJJOA'
SecretKey = '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'

# bucket name in S3
Bucket = 'tsudat.aifdr.org'

# name of run_tsudat() file, here and on EC2 (name change)
Ec2RunTsuDAT = 'save_run_tsudat.py'
Ec2RunTsuDATOnEC2 = 'run_tsudat.py'

# names of additional required files
ReqdFiles = ['export_depthonland_max.py', 'export_newstage_max.py']

# name of the JSON data file
JsonDataFilename = 'data.json'

# name of the fault name file (in multimux directory)
FaultNameFilename = 'fault_list.txt'

# match any number of spaces beteen fields
SpacesPattern = re.compile(' +')

# dictionary to handle attribute renaming from JSON->project
# 'UI_name': 'ANUGA_name',
RenameDict = {'mesh_friction': 'friction',
              'smoothing': 'alpha',
              'end_time': 'finaltime',
              'layers': 'var',
              'raster_resolution': 'cell_size',
              'elevation_data': 'point_filenames',
             }

# major directories under user/project/scenario/setup base directory
MajorSubDirs = ['topographies', 'polygons', 'boundaries', 'outputs',
                'gauges', 'meshes', 'scripts']


# define a 'project' object
class Project(object):
    pass

project = Project()

# populate with some fixed values
project.multi_mux = True


def make_dir_zip(dirname, zipname):
    """Make a ZIP file from a directory.

    dirname  path to directory to zip up
    zipname  path to ZIP file to create
    """

    def recursive_zip(zipf, directory):
        ls = os.listdir(directory)

        for f in ls:
            f_path = os.path.join(directory, f)
            if os.path.isdir(f_path):
                recursive_zip(zipf, f_path)
            else:
                zipf.write(f_path, f_path, zipfile.ZIP_DEFLATED)

    zf = zipfile.ZipFile(zipname, mode='w')
    recursive_zip(zf, dirname)
    zf.close()


def make_tsudat_dir(base, user, proj, scen, setup, event,
                    nuke=False, make_files=False):
    """Create a TsuDAT2 work directory.

    base        path to base of new directory structure
    user        user name
    proj        project name
    scen        scenario name
    setup       type of run ('trial', etc)
    event       event number
    nuke        optional - destroy any existing structure first
    make_files  create 'placeholder' files (for debug/documentation)

    Creates a TSUDAT directory structure under the 'base' path.
    If 'nuke' is True, delete any structure under base/user/proj/scen/setup.

    Returns a tuple of paths to places under 'base' required by the UI:
        (raw_elevation, bondaries, meshes, polygons, gauges)
    """

    global ScriptsDir

    def touch(path):
        """Helper function to do a 'touch' for a file."""

        with file(path, 'a'):
            os.utime(path, None)

    def makedirs_noerror(path):
        """Helper function to create a directory tree, ignoring errors."""

        try:
            os.makedirs(path)
        except OSError:
            pass            # ignore "already there' errors

    # create base directory
    run_dir = os.path.join(base, user, proj, scen, setup)
    if nuke:
        shutil.rmtree(run_dir, ignore_errors=True)
    makedirs_noerror(run_dir)

    # create the 'raw_elevation' directory for a project
    raw_elevation = os.path.join(base, user, proj, 'raw_elevation')
    makedirs_noerror(raw_elevation)

    # now create major sub-dirs under $setup
    for sd in MajorSubDirs:
        makedirs_noerror(os.path.join(run_dir, sd))

    # get extra return paths
    boundaries = os.path.join(run_dir, 'boundaries')
    meshes = os.path.join(run_dir, 'meshes')
    polygons = os.path.join(run_dir, 'polygons')
    gauges = os.path.join(run_dir, 'gauges')

    # save scripts path globally to help run_tsudat()
    ScriptsDir = os.path.join(run_dir, 'scripts')

    # now create example files if required
    if make_files:
        touch(os.path.join(raw_elevation, 'raw_elevation1.asc'))
        touch(os.path.join(raw_elevation, 'raw_elevation2.asc'))

        path = os.path.join(run_dir, 'topographies')
        touch(os.path.join(path, 'combined_elevation.pts'))
        touch(os.path.join(path, 'combined_elevation.txt'))

        touch(os.path.join(boundaries, 'event_%d.lst' % event))
        touch(os.path.join(boundaries, 'landward_boundary.csv'))
        touch(os.path.join(boundaries, 'urs_order.csv'))

        path = os.path.join(run_dir, 'outputs')
        touch(os.path.join(path, 'generated_files'))

        path = os.path.join(run_dir, 'gauges')
        touch(os.path.join(path, 'gauges_final.csv'))

        touch(os.path.join(meshes, 'meshes.msh'))

        touch(os.path.join(polygons, 'polygon_files'))

    # a fudge - because the zip process doesn't save empty directories
    # we must write a small file into empty directories
    placeholder = os.path.join(meshes, '.placeholder')
    with open(placeholder, 'w') as fd:
        pass

    # return paths to various places under 'base'
    return (run_dir, raw_elevation, boundaries, meshes, polygons, gauges)


def setup_model():
    """Perform sanity checks.

    The checks here can be simpler than for full-blown ANUGA as the directory
    structure is automatically generated.
    """

    # flag - we check many things and then don't proceed if anything wrong
    sanity_error = False               # checked at bottom of this file

    #####
    # check directory Structure
    #####

    if not os.path.exists(project.working_directory):
        log.error("Sorry, working directory '%s' doesn't exist"
                  % project.working_directory)
        sanity_error = True

    if not os.path.exists(project.mux_directory):
        log.error("Sorry, mux directory '%s' doesn't exist"
                  % project.mux_directory)
        sanity_error = True

    if not os.path.exists(project.anuga_folder):
        log.error("Sorry, ANUGA directory '%s' doesn't exist"
                  % project.anuga_folder)
        sanity_error = True

    if not os.path.exists(project.topographies_folder):
        log.error("Sorry, topo directory '%s' doesn't exist"
                  % project.topographies_folder)
        sanity_error = True

    if not os.path.exists(project.polygons_folder):
        log.error("Sorry, polygon directory '%s' doesn't exist"
                  % project.polygons_folder)
        sanity_error = True

    if not os.path.exists(project.boundaries_folder):
        log.error("Sorry, boundaries directory '%s' doesn't exist"
                  % project.boundaries_folder)
        sanity_error = True

    if not os.path.exists(project.output_folder):
        log.error("Sorry, outputs directory '%s' doesn't exist"
                  % project.output_folder)
        sanity_error = True

    if not os.path.exists(project.gauges_folder):
        log.error("Sorry, gauges directory '%s' doesn't exist"
                  % project.gauges_folder)
        sanity_error = True

    if not os.path.exists(project.meshes_folder):
        log.error("Sorry, meshes directory '%s' doesn't exist"
                  % project.meshes_folder)
        sanity_error = True

    if not os.path.exists(project.mux_data_folder):
        log.error("Sorry, mux data directory '%s' doesn't exist"
                  % project.mux_data_folder)
        sanity_error = True

    # generate the event.lst file for the event
    get_multimux(project.event, project.multimux_folder, project.mux_input)

    # if multi_mux is True, check if multi-mux file exists
    if project.multi_mux:
        if not os.path.exists(project.mux_input):
            log.error("Sorry, MUX input file '%s' doesn't exist"
                      % project.mux_input)
            sanity_error = True

    if not os.path.exists(project.event_folder):
        log.error("Sorry, you must generate event %s with EventSelection."
                  % project.event)
        sanity_error = True

    #####
    # determine type of run, set some parameters depending on type
    #####

    if project.setup == 'trial':
        project.scale_factor = 100
        project.time_thinning = 96
        project.yieldstep = 240
    elif project.setup == 'basic':
        project.scale_factor = 4
        project.time_thinning = 12
        project.yieldstep = 120
    elif project.setup == 'final':
        project.scale_factor = 1
        project.time_thinning = 4
        project.yieldstep = 60
    else:
        log.error("Sorry, you must set the 'setup' variable to one of:"
                  '   trial - coarsest mesh, fast\n'
                  '   basic - coarse mesh\n'
                  '   final - fine mesh, slowest\n'
                  '\n'
                  "'setup' was set to '%s'" % project.setup)
        sanity_error = True

    #####
    # check for errors detected above.
    #####

    if sanity_error:
        msg = 'You must fix the above errors before continuing.'
        raise Exception(msg)

    #####
    # Reading polygons and creating interior regions
    #####

    # Create list of interior polygons with scaling factor
    project.interior_regions = []
    for (filename, maxarea) in project.interior_regions_data:
        polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
                                                  filename))
        project.interior_regions.append([polygon,
                                         maxarea*project.scale_factor])

    # Initial bounding polygon for data clipping
    project.bounding_polygon = anuga.read_polygon(os.path.join(
                                                      project.polygons_folder,
                                                      project.bounding_polygon))
    project.bounding_maxarea = project.bounding_polygon_maxarea \
                               * project.scale_factor

    # Estimate the number of triangles
    triangle_min = number_mesh_triangles(project.interior_regions,
                                         project.bounding_polygon,
                                         project.bounding_maxarea)

    log.info('minimum estimated number of triangles=%d' % triangle_min)


def get_multimux(event, multimux_dir, output_file):
    """Does exactly what David Burbidge's 'get_multimux' program does.

    event         event ID
    multimux_dir  path to the multimux files
    output_file   path to file to write
    """

    # get data
    filename = os.path.join(multimux_dir, FaultNameFilename)
    try:
        fd = open(filename, "r")
        fault_names = [ fn.strip() for fn in fd.readlines() ]
        fd.close()
    except IOError, msg:
        raise RuntimeError(1, "Error reading file: %s" % msg)

    # open the output file
    try:
        outfd = open(output_file, "w")
    except IOError, msg:
        raise Exception('Error opening output file: %s' % msg)

    # handle each fault
    nquake = 0
    for fn in fault_names:
        # create the filename for the multimux data file
        mmx_filename = 'i_multimux-%s' % fn
        mmx_filename = os.path.join(multimux_dir, mmx_filename)

        # Read all data in file, checking as we go
        try:
            infd = open(mmx_filename, "r")
        except IOError, msg:
            raise Exception('Error opening file: %s' % msg)

        # check fault name in file is as expected
        mux_faultname = infd.readline().strip()
        if mux_faultname != fn:
            raise Exception("Error in file %s: fault name in file isn't %s"
                            % (mmx_filename, fn))

        # read data
        while True:
            # get number of subfaults, EOF means finished
            try:
                nsubfault = infd.readline()
            except IOError:
                raise Exception("Error reading file %s: EOF reading event"
                                % mmx_filename)

            if not nsubfault:
                break
            nsubfault = int(nsubfault)

            nquake += 1
            if nquake == event:
                outfd.write(' %d\n' % nsubfault)
                for i in range(nsubfault):
                    line = infd.readline()
                    (subfaultname, slip, prob, mag, _) = \
                                   SpacesPattern.split(line, maxsplit=4)
                    subfaultname = subfaultname.strip()
                    slip = float(slip)
                    outfd.write(" %s %g\n" % (subfaultname, slip))
            else:
                for i in range(nsubfault):
                    try:
                        infd.readline()
                    except IOError:
                        raise Exception("Something wrong at bottom of file %s"
                                        % mux_faultname)

        infd.close()
    outfd.close()


def build_elevation():
    """Create combined elevation data.

    Combine all raw elevation data and clip to bounding polygon.
    """

    # Create Geospatial data from ASCII files
    geospatial_data = {}
    for filename in project.ascii_grid_filenames:
        log.info('Reading elevation file %s' % filename)
        absolute_filename = os.path.join(project.raw_elevation_folder, filename)
        anuga.asc2dem(absolute_filename+'.asc',
                      use_cache=False, verbose=False)
        anuga.dem2pts(absolute_filename+'.dem', use_cache=False, verbose=False)

        G_grid = anuga.geospatial_data.\
                     Geospatial_data(file_name=absolute_filename+'.pts',
                                     verbose=False)

        geospatial_data[filename] = G_grid.clip(project.bounding_polygon)

    # Create Geospatial data from TXT files
    for filename in project.point_filenames:
        log.info('Reading elevation file %s' % filename)
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
    # DO WE NEED THIS?
    G.export_points_file(project.combined_elevation + '.txt')


def get_sts_gauge_data(filename, verbose=False):
    """Get gauges (timeseries of index points)."""

    fid = NetCDFFile(filename+'.sts', 'r')      # Open existing file for read
    permutation = fid.variables['permutation'][:]
    x = fid.variables['x'][:] + fid.xllcorner   # x-coordinates of vertices
    y = fid.variables['y'][:] + fid.yllcorner   # y-coordinates of vertices
    points = num.transpose(num.asarray([x.tolist(), y.tolist()]))
    time = fid.variables['time'][:] + fid.starttime
    elevation = fid.variables['elevation'][:]

    basename = 'sts_gauge'
    quantity_names = ['stage', 'xmomentum', 'ymomentum']
    quantities = {}
    for i, name in enumerate(quantity_names):
        quantities[name] = fid.variables[name][:]

    #####
    # Get maximum wave height throughout timeseries at each index point
    #####

    maxname = 'max_sts_stage.csv'
    fid_max = open(os.path.join(project.event_folder, maxname), 'w')
    fid_max.write('index, x, y, max_stage \n')
    for j in range(len(x)):
        index = permutation[j]
        stage = quantities['stage'][:,j]
        xmomentum = quantities['xmomentum'][:,j]
        ymomentum = quantities['ymomentum'][:,j]

        fid_max.write('%d, %.6f, %.6f, %.6f\n'
                      % (index, x[j], y[j], max(stage)))

    #####
    # Get minimum wave height throughout timeseries at each index point
    #####

    minname = 'min_sts_stage.csv'
    fid_min = open(os.path.join(project.event_folder, minname), 'w')
    fid_min.write('index, x, y, max_stage \n')
    for j in range(len(x)):
        index = permutation[j]
        stage = quantities['stage'][:,j]
        xmomentum = quantities['xmomentum'][:,j]
        ymomentum = quantities['ymomentum'][:,j]

        fid_min.write('%d, %.6f, %.6f, %.6f\n' %(index, x[j], y[j], min(stage)))

        out_file = os.path.join(project.event_folder,
                                basename+'_'+str(index)+'.csv')
        fid_sts = open(out_file, 'w')
        fid_sts.write('time, stage, xmomentum, ymomentum \n')

        #####
        # End of the get gauges
        #####

        for k in range(len(time)-1):
            fid_sts.write('%.6f, %.6f, %.6f, %.6f\n'
                          % (time[k], stage[k], xmomentum[k], ymomentum[k]))

        fid_sts.close()
    fid.close()

    return (quantities, elevation, time)


def build_urs_boundary(event_file, output_dir):
    """Build a boundary STS file from a set of MUX files.

    event_file  name of mux meta-file or single mux stem
    output_dir  directory to write STS data to
    """

    # if we are using an EventSelection multi-mux file
    if project.multi_mux:
        # get the mux+weight data from the meta-file (in <boundaries>)
        mux_event_file = os.path.join(project.event_folder, event_file)
        try:
            fd = open(mux_event_file, 'r')
            mux_data = fd.readlines()
            fd.close()
        except IOError, e:
            msg = 'File %s cannot be read: %s' % (mux_event_file, str(e))
            raise Exception(msg)
        except:
            raise

        # first line of file is # filenames+weight in rest of file
        num_lines = int(mux_data[0].strip())
        mux_data = mux_data[1:]

        # quick sanity check on input mux meta-file
        if num_lines != len(mux_data):
            msg = ('Bad file %s: %d data lines, but line 1 count is %d'
                   % (event_file, len(mux_data), num_lines))
            raise Exception(msg)

        # Create filename and weights lists.
        # Must chop GRD filename just after '*.grd'.
        mux_filenames = []
        for line in mux_data:
            muxname = line.strip().split()[0]
            split_index = muxname.index('.grd')
            muxname = muxname[:split_index+len('.grd')]
            muxname = os.path.join(project.mux_data_folder, muxname)
            mux_filenames.append(muxname)

        mux_weights = [float(line.strip().split()[1]) for line in mux_data]

        # Call legacy function to create STS file.
        anuga.urs2sts(mux_filenames, basename_out=output_dir,
                      ordering_filename=project.urs_order,
                      weights=mux_weights, verbose=False)
    else:                           # a single mux stem file, assume 1.0 weight
        log.info('using single-mux file %s' % mux_file)

        mux_file = os.path.join(project.event_folder, event_file)
        mux_filenames = [mux_file]

        weight_factor = 1.0
        mux_weights = weight_factor*num.ones(len(mux_filenames), num.Float)

        order_filename = project.urs_order

        # Create ordered sts file
        anuga.urs2sts(mux_filenames, basename_out=output_dir,
                      ordering_filename=order_filename,
                      weights=mux_weights, verbose=False)

    # report on progress so far
    sts_file = os.path.join(project.event_folder, project.scenario_name)
    log.info('URS boundary file=%s' % sts_file)

    (quantities, elevation, time) = get_sts_gauge_data(sts_file, verbose=False)
    log.debug('%d %d' % (len(elevation), len(quantities['stage'][0,:])))


def adorn_project(json_data):
    """Adorn the project object with data from the json file.

    json_data  path to the UI JSON data file

    Also adds extra project attributes derived from JSON data.
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

        # allow renaming of attributes here
        new_key = RenameDict.get(key, key)

        # set new attribute in project object
        project.__setattr__(new_key, value)

    # add extra derived attributes
    # paths to various directories
    project.anuga_folder = os.path.join(project.working_directory, project.user,
                                        project.project, project.scenario_name,
                                        project.setup)
    project.topographies_folder = os.path.join(project.anuga_folder,
                                               'topographies')
    project.polygons_folder = os.path.join(project.anuga_folder, 'polygons')
    project.boundaries_folder = os.path.join(project.anuga_folder, 'boundaries')
    project.output_folder = os.path.join(project.anuga_folder, 'outputs')
    project.gauges_folder = os.path.join(project.anuga_folder, 'gauges')
    project.meshes_folder = os.path.join(project.anuga_folder, 'meshes')
    project.event_folder = project.boundaries_folder
    project.raw_elevation_folder = os.path.join(project.working_directory,
                                                project.user,
                                                project.project,
                                                'raw_elevation')

    # MUX data files
    # Directory containing the MUX data files to be used with EventSelection.
    project.mux_data_folder = os.path.join(project.mux_directory, 'mux')
    project.multimux_folder = os.path.join(project.mux_directory, 'multimux')

    project.mux_input_filename = 'event_%d.lst' % project.event

    #####
    # Location of input and output data
    #####

    # The stem path of the all elevation, generated in build_elevation()
    project.combined_elevation = os.path.join(project.topographies_folder,
                                              'combined_elevation')

    # The absolute pathname of the mesh, generated in run_model.py
    project.meshes = os.path.join(project.meshes_folder, 'meshes.msh')

    # The pathname for the urs order points, used within build_urs_boundary.py
    project.urs_order = os.path.join(project.boundaries_folder, 'urs_order.csv')

    # The absolute pathname for the landward points of the bounding polygon,
    # Used within run_model.py)
    project.landward_boundary = os.path.join(project.boundaries_folder,
                                             'landward_boundary.csv')

    # The absolute pathname for the .sts file, generated in build_boundary.py
    project.event_sts = project.boundaries_folder

    # The absolute pathname for the gauges file
    project.gauges = os.path.join(project.gauges_folder, 'gauges_final.csv')

    # full path to where MUX files (or meta-files) live
    project.mux_input = os.path.join(project.event_folder,
                                     'event_%d.lst' % project.event)

    # not sure what this is for
    project.land_initial_conditions = []

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


def excepthook(type, value, tb):
    """Exception hook routine."""

    msg = '\n' + '='*80 + '\n'
    msg += 'Uncaught exception:\n'
    msg += ''.join(traceback.format_exception(type, value, tb))
    msg += '='*80 + '\n'
    log.critical(msg)


def start_ami(ami, key_name='gsg-keypair', instance_type='m1.large',
              user_data=None):
    """
    """

    ec2 = boto.connect_ec2(AccessKey, SecretKey)
    if user_data is None:
        user_data = ''
    reservation = ec2.run_instances(image_id=ami, key_name=key_name,
                                    instance_type=instance_type,
                                    user_data=user_data)

    # Wait a minute or two while it boots
    instance = reservation.instances[0]
    while True:
        instance.update()
        if instance.state == 'running':
            break
        time.sleep(1)

    return instance


def dump_project_py():
    """Debug routine - dump project attributes to the log."""

    # list all project.* attributes
    for key in dir(project):
        if not key.startswith('__'):
            try:
                log.info('project.%s=%s' % (key, eval('project.%s' % key)))
            except AttributeError:
                pass


def dump_json_to_file(project, json_file):
    """Dump project object back to a JSON file.

    project  the project object to dump
    json_file  the file to dump JSON to

    Dump all 'non-special' attributes of the object.
    """

    ui_dict = {}
    for attr_name in dir(project):
        if not attr_name.startswith('_'):
            ui_dict[attr_name] = project.__getattribute__(attr_name)
     
    with open(json_file, 'w') as fd:
        json.dump(ui_dict, fd, indent=2, separators=(',', ':'))


def run_tsudat(json_data):
    """Run ANUGA on the Amazon EC2.

    json_data  the path to the JSON data file
    """

    # plug our exception handler into the python system
    sys.excepthook = excepthook

    # get JSON data and adorn project object with its data
    adorn_project(json_data)

    # set logfile to be in run output folder
    if project.debug:
        log.log_logging_level = log.DEBUG
    log.log_filename = os.path.join(project.output_folder, 'ui.log')
    if project.debug:
        dump_project_py()

    # do all required data generation before EC2 run
    log.info('#'*90)
    log.info('# Preparing simulation')
    log.info('#'*90)
    setup_model()
    build_elevation()
    build_urs_boundary(project.mux_input_filename, project.event_sts)

    # copy all required python modules to scripts directory
    ec2_name = os.path.join(ScriptsDir, Ec2RunTsuDATOnEC2)
    log.debug("Copying EC2 run file '%s' to scripts directory '%s'."
              % (Ec2RunTsuDAT, ec2_name))
    shutil.copy(Ec2RunTsuDAT, ec2_name)
    for extra in ReqdFiles:
        shutil.copy(extra, ScriptsDir)

    # dump the current 'projects' object back into JSON, put in 'scripts'
    dump_project_py()
    json_file = os.path.join(ScriptsDir, JsonDataFilename)
    log.debug('Dumping JSON to file %s' % json_file)
    dump_json_to_file(project, json_file)

    # bundle up the working directory, put it into S3
    # move just what we want to a temporary directory
    zipname = ('%s-%s-%s-%s.zip'
               % (project.user, project.project,
                  project.scenario_name, project.setup))
    log.debug('Making zip %s' % zipname)
    make_dir_zip(project.working_directory, zipname)

    s3_name = 'input-data/%s' % zipname
    try:
        access_key = os.environ['EC2_ACCESS_KEY']
        secret_key = os.environ['EC2_SECRET_ACCESS_KEY']
        s3 = boto.connect_s3(access_key, secret_key)
        access_key = 'DEADBEEF'
        secret_key = 'DEADBEEF'
        del access_key, secret_key

        bucket = s3.create_bucket(Bucket)
        key = bucket.new_key(s3_name)
        log.debug('Creating S3 file: %s/%s' % (Bucket, s3_name))
        key.set_contents_from_filename(zipname)
        log.debug('Done!')
        key.set_acl('public-read')
    except boto.exception.S3ResponseError, e:
        log.critical('S3 error: %s' % str(e))
        print('S3 error: %s' % str(e))
        sys.exit(10)

    # clean up the local filesystem
    dir_path = os.path.join(project.working_directory, project.user)
    log.debug('Deleting work directory: %s' % dir_path)
    shutil.rmtree(dir_path)

    # start the EC2 instance we are using
    user_data = ' '.join([project.user, project.project, project.scenario_name,
                          project.setup, project.working_directory,
                          'debug' if project.debug else 'production'])
    log.info('Starting AMI %s, user_data=%s' % (DefaultAmi, str(user_data)))
    try:
        instance = start_ami(DefaultAmi, user_data=''.join(user_data))
    except boto.exception.EC2ResponseError, e:
        log.critical('EC2 error: %s' % str(e))
        print('EC2 error: %s' % str(e))
        sys.exit(10)

    print('*'*80)
    print('* Started instance: %s' % instance.dns_name)
    print('*'*80)
    log.info('Started instance: %s' % instance.dns_name)
