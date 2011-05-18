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
DefaultAmi = 'ami-54a55b3d'  # Ubuntu_10.04_TsuDAT_2.0.28

# keypair used to start instance
#DefaultKeypair = 'gsg-keypair'
DefaultKeypair = 'tsudat2'

# various S3 default things
DefaultSQSQueuename = 'tsudat_aifdr_org'
DefaultS3Bucket = 'tsudat.aifdr.org'
DefaultInputS3DataDir = 'input-data'
DefaultOutputS3DataDir = 'output-data'
DefaultAbortS3DataDir = 'abort'
DefaultURSOrderFile = 'urs_order.csv'

# define defaults for various pieces S3 things
# used by default_project_values()
# format: iterable of (<name>, <default value>)
DefaultJSONValues = (('sqs_queue_name', DefaultSQSQueuename),
                     ('S3Bucket', DefaultS3Bucket),
                     ('InputS3DataDir', DefaultInputS3DataDir),
                     ('OutputS3DataDir', DefaultOutputS3DataDir),
                     ('AbortS3DataDir', DefaultAbortS3DataDir),
                     ('urs_order_file', DefaultURSOrderFile),
                    )

# dictionary to handle attribute renaming from JSON->project
# format: {'UI_name': 'ANUGA_name', ...}
RenameDict = {'mesh_friction': 'friction',
              'smoothing': 'alpha',
              'end_time': 'finaltime',
              'layers': 'var',
              'raster_resolution': 'cell_size',
              'elevation_data_list': 'point_filenames',
             }

# name of run_tsudat() file, here and on EC2 (name change)
Ec2RunTsuDAT = 'ec2_run_tsudat.py'
Ec2RunTsuDATOnEC2 = 'run_tsudat.py'

# names of additional required files in S3 bucket file
RequiredFiles = ['export_depthonland_max.py',
                 'export_newstage_max.py']

# name of the JSON data file
JsonDataFilename = 'data.json'

# name of the fault name file (in multimux directory)
FaultNameFilename = 'fault_list.txt'

# match any number of spaces between fields
SpacesPattern = re.compile(' +')

# major directories under user/project/scenario/setup base directory
MajorSubDirs = ['topographies', 'polygons', 'boundaries', 'outputs',
                'gauges', 'meshes', 'scripts']


# define a 'project' object
class Project(object):
    pass

project = Project()

# populate with some fixed values
project.multi_mux = True


def abort(msg):
    """Abort the process."""

    print(msg)
    log.critical(msg)
    sys.exit(10)

def make_dir_zip(dirname, zipname):
    """Make a ZIP file from a directory.

    dirname  path to directory to zip up
    zipname  path to ZIP file to create
    """

    os.system('zip -q -r %s %s' % (zipname, dirname))

def make_tsudat_dir(base, user, proj, scen, setup, event, nuke=False):
    """Create a TsuDAT2 work directory.

    base        path to base of new directory structure
    user        user name
    proj        project name
    scen        scenario name
    setup       type of run ('trial', etc)
    event       event number
    nuke        optional - destroy any existing structure first

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
        new_dir = os.path.join(run_dir, sd)
        makedirs_noerror(new_dir)

    # get extra return paths
    boundaries = os.path.join(run_dir, 'boundaries')
    meshes = os.path.join(run_dir, 'meshes')
    polygons = os.path.join(run_dir, 'polygons')
    gauges = os.path.join(run_dir, 'gauges')

    # save scripts path globally to help run_tsudat()
    ScriptsDir = os.path.join(run_dir, 'scripts')

    # a fudge - because the zip process doesn't save empty directories
    # we must write a small file into empty directories we zip
    placeholder = os.path.join(meshes, '.placeholder')
    with open(placeholder, 'w') as fd:
        pass

    # return paths to various places under 'base'
    return (run_dir, raw_elevation, boundaries, meshes, polygons, gauges)

def create_urs_order():
    """Create the urs order file.

    Uses landward boundary data (LB) and interior hazard points data (iHP).
        1. Read LB data
        2. Read iHP data
        3. Get last LB point
        4. Get distance from last LB to first and last iHP
        5. if last LB closer to last iHP, invert iHP order
        6. write iHP to urs order file
    """

    # get landward boundary data: lb_data = [(e,n), ...]
    lb_file = os.path.join(project.boundaries_folder, project.landward_boundary_file)
    with open(lb_file, 'r') as fp:
        lines = fp.readlines()
    lb_data = []
    for line in lines:
        (e, n) = line.split(',')
        e = float(e.strip())
        n = float(n.strip())
        lb_data.append((e, n))

    # get interior HP data: hp_data = [(e,n), ...]
    hp_file = os.path.join(project.boundaries_folder, project.interior_hazard_points_file)
    with open(hp_file, 'r') as fp:
        lines = fp.readlines()
    hp_data = []
    for line in lines:
        (hp_id, lon, lat, e, n) = line.split(',')
        hp_id = int(hp_id.strip())
        lon = float(lon.strip())
        lat = float(lat.strip())
        e = float(e.strip())
        n = float(n.strip())
        hp_data.append((e, n, hp_id, lon, lat))

    # get last LB and first and last iHP, get distances (squared)
    (last_lb_x, last_lb_y) = lb_data[-1]
    (first_hp_x, first_hp_y, _, _, _) = hp_data[0]
    (last_hp_x, last_hp_y, _, _, _) = hp_data[-1]
    d2_first = (first_hp_x-last_lb_x)**2 + (first_hp_y-last_lb_y)**2
    d2_last = (last_hp_x-last_lb_x)**2 + (last_hp_y-last_lb_y)**2

    # if distance to last < distance to first invert hp_data list
    if d2_last < d2_first:
        hp_data.reverse()

    # now create urs_order file
    urs_file = os.path.join(project.boundaries_folder, project.urs_order_file)
    with open(urs_file, 'wb') as fp:
        fp.write('index,longitude,latitude\n')
        for (_, _, hp_id, lon, lat) in hp_data:
            fp.write('%d,%f,%f\n' % (hp_id, lon, lat))
    project.urs_order_file = urs_file

def setup_model():
    """Perform sanity checks and generate data.

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
    get_multimux(project.event_number, project.multimux_folder, project.mux_input)

    # if multi_mux is True, check if multi-mux file exists
    if project.multi_mux:
        if not os.path.exists(project.mux_input):
            log.error("Sorry, MUX input file '%s' doesn't exist"
                      % project.mux_input)
            sanity_error = True

    if not os.path.exists(project.event_folder):
        log.error("Sorry, you must generate event %s with EventSelection."
                  % project.event_number)
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
    # Create the urs order file
    #####

    create_urs_order()

    #####
    # Reading polygons and creating mesh interior regions
    #####

    # Create list of interior polygons with scaling factor
    project.interior_regions = []
    for (irtype, filename, maxarea) in project.interior_regions_list:
        if irtype.lower() == 'mesh':
            polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
                                                      filename))
            project.interior_regions.append([polygon,
                                             maxarea*project.scale_factor])

    # Initial bounding polygon for data clipping
    project.bounding_polygon = anuga.read_polygon(os.path.join(
                                                      project.polygons_folder,
                                                      project.bounding_polygon_file))
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

    # if no elevation to combine, we *must* have a combined elevation file
    if not project.ascii_grid_filenames and not project.point_filenames:
        if not project.combined_elevation_file:
            msg = 'No raw elevation data and no combined elevation data!?'
            abort(msg)
        return

    # user wants us to create combined elevation, make output filename
    project.combined_elevation_file = os.path.join(
                                              project.topographies_folder,
                                              'combined_elevation.pts')

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

    G.export_points_file(project.combined_elevation_file)

    # Use for comparision in ARC
    # DO WE NEED THIS?
    try:
        (stem, _) = project.combined_elevation_file.rsplit('.', 1)
    except ValueError:
        stem = project.combined_elevation_file
    G.export_points_file(stem + '.txt')

def get_sts_gauge_data(filename, verbose=False):
    """Get gauges (timeseries of index points).
    
    Returns a tuple containing:
        (quantities, elevation, time, gen_files)
    """

    log.debug('get_sts_gauge_data: filename=%s' % filename)

    # prepare list to return generated filenames in
    gen_files = []

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

    maxname = os.path.join(project.output_folder, 'max_sts_stage.csv')
    gen_files.append(maxname)
    fid_max = open(maxname, 'w')
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

    minname = os.path.join(project.output_folder, 'min_sts_stage.csv')
    gen_files.append(minname)
    fid_min = open(minname, 'w')
    fid_min.write('index, x, y, max_stage \n')
    for j in range(len(x)):
        index = permutation[j]
        stage = quantities['stage'][:,j]
        xmomentum = quantities['xmomentum'][:,j]
        ymomentum = quantities['ymomentum'][:,j]

        fid_min.write('%d, %.6f, %.6f, %.6f\n' %(index, x[j], y[j], min(stage)))

        out_file = os.path.join(project.output_folder,
                                basename+'_'+str(index)+'.csv')
        gen_files.append(out_file)
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

    return (quantities, elevation, time, gen_files)

def build_urs_boundary(event_file, output_dir):
    """Build a boundary STS file from a set of MUX files.

    event_file  name of mux meta-file or single mux stem
    output_dir  directory to write STS data to

    Returns a list of generated 'sts_gauge' files.
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
                      ordering_filename=project.urs_order_file,
                      weights=mux_weights, verbose=False)
    else:                           # a single mux stem file, assume 1.0 weight
        log.info('using single-mux file %s' % mux_file)

        mux_file = os.path.join(project.event_folder, event_file)
        mux_filenames = [mux_file]

        weight_factor = 1.0
        mux_weights = weight_factor*num.ones(len(mux_filenames), num.Float)

        order_filename = project.urs_order_file

        # Create ordered sts file
        anuga.urs2sts(mux_filenames, basename_out=output_dir,
                      ordering_filename=order_filename,
                      weights=mux_weights, verbose=False)

    # report on progress so far
    sts_file = os.path.join(project.event_folder, project.sts_filestem)
    log.info('STS filestem=%s' % sts_file)

    (quantities, elevation,
     time, gen_files) = get_sts_gauge_data(sts_file, verbose=False)
    log.debug('%d %d' % (len(elevation), len(quantities['stage'][0,:])))

    return gen_files

def define_default(name, default):
    """Check if a project attribute is defined, default it if not.

    name   name of attribute to check (string)
    default  default value if attribute isn't defined
    """

    try:
        eval('project.%s' % name)
    except AttributeError:
        setattr(project, name, default)
    else:
        exec('value = project.%s' % name)
        if not value:
            setattr(project, name, default)

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

    # set default values for attributes that aren't defined or not provided
    define_default('mesh_file', '%s.msh' % project.scenario)

    define_default('debug', False)
    define_default('force_run', True)

    # add extra derived attributes
    # paths to various directories
    project.anuga_folder = os.path.join(project.working_directory, project.user,
                                        project.project, project.scenario,
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

    project.mux_input_filename = 'event_%d.lst' % project.event_number

    #####
    # Location of input and output data
    # Generate full paths to data files
    #####

    # The complete path to the elevation, generated in build_elevation()
    if project.combined_elevation_file:
        project.combined_elevation_file = os.path.join(
                                              project.topographies_folder,
                                              project.combined_elevation_file)

    # The absolute pathname of the mesh, generated in run_model.py
    if project.mesh_file:
        project.mesh_file = os.path.join(project.meshes_folder,
                                         project.mesh_file)

    # The absolute pathname for the landward points of the bounding polygon,
    # Used within run_model.py)
    project.landward_boundary_file = os.path.join(project.boundaries_folder,
                                             project.landward_boundary_file)

    # The absolute pathname for the .sts file, generated in build_boundary.py
    project.event_sts = project.boundaries_folder

    # The absolute pathname for the gauges file
    project.gauge_file = os.path.join(project.gauges_folder, project.gauge_file)

    # full path to where MUX files (or meta-files) live
    project.mux_input = os.path.join(project.event_folder,
                                     'event_%d.lst' % project.event_number)

    # not sure what this is for
    project.land_initial_conditions = []

def excepthook(type, value, tb):
    """Exception hook routine."""

    msg = '\n' + '='*80 + '\n'
    msg += 'Uncaught exception:\n'
    msg += ''.join(traceback.format_exception(type, value, tb))
    msg += '='*80 + '\n'
    log.critical(msg)

def start_ami(ami, key_name=DefaultKeypair, instance_type='m1.large',
              user_data=None):
    """Start the configured AMI, wait until it's running.

    ami            the ami ID ('ami-????????')
    key_name       the keypair name
    instance_type  type of instance to run
    user_data      the user data string to pass to instance
    """

    access_key = os.environ['EC2_ACCESS_KEY']
    secret_key = os.environ['EC2_SECRET_ACCESS_KEY']
    ec2 = boto.connect_ec2(access_key, secret_key)
    access_key = 'DEADBEEF'
    secret_key = 'DEADBEEF'
    del access_key, secret_key

    if user_data is None:
        user_data = ''

    reservation = ec2.run_instances(image_id=ami, key_name=key_name,
                                    instance_type=instance_type,
                                    user_data=user_data)
    # got some sort of race - "instance not found"? - try waiting a bit
    time.sleep(1)

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

def s3_connect():
    """Get an S3 connection object.

    Returns an S3 connection object.

    Tries hard not to expose keys in memory.
    """

    access_key = os.environ['EC2_ACCESS_KEY']
    secret_key = os.environ['EC2_SECRET_ACCESS_KEY']
    s3 = boto.connect_s3(access_key, secret_key)
    access_key = 'DEADBEEF'
    secret_key = 'DEADBEEF'
    del access_key, secret_key

    return s3

def default_project_values():
    """Default certain values if they don't appear in the project object."""

    for (name, value) in DefaultJSONValues:
        if getattr(project, name, None) is None:
            setattr(project, name, value)

def get_minmaxAOI():
    """Figure out minmaxAOI values from AOI file.
    
    Populates the following 'project' attributes:
        xminAOI, xmaxAOI, yminAOI, ymaxAOI
    """

    for (irtype, filename, _) in project.interior_regions_list:
        if irtype.lower() == 'aoi':
            path = os.path.join(project.polygons_folder, filename)
            (xminAOI, xmaxAOI) = (9999999999.0, -1.0)
            (yminAOI, ymaxAOI) = (9999999999.0, -1.0)
            with open(path, 'r') as fp:
                lines = fp.readlines()
            for line in lines:
                (x, y) = line.split(',')
                x = float(x.strip())
                y = float(y.strip())
                xminAOI = min(xminAOI, x)
                xmaxAOI = max(xmaxAOI, x)
                yminAOI = min(yminAOI, y)
                ymaxAOI = max(ymaxAOI, y)
            project.xminAOI = xminAOI
            project.xmaxAOI = xmaxAOI
            project.yminAOI = yminAOI
            project.ymaxAOI = ymaxAOI
            return

    msg = ("Didn't find 'aoi' type in project.interior_regions_list: %s"
           % str(project.interior_regions_list))
    abort(msg)


def run_tsudat(json_data):
    """Run ANUGA on the Amazon EC2.

    json_data  the path to the JSON data file

    Returns the boto instance object for the running image.
    """

    # plug our exception handler into the python system
    sys.excepthook = excepthook

    # get JSON data and adorn project object with its data
    adorn_project(json_data)

    # default certain values if not supplied in JSON data
    default_project_values()

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

    log.info('Calling: setup_model()')
    setup_model()

    log.info('Calling: build_elevation()')
    build_elevation()

    log.info('Calling: build_urs_boundary()')
    # create .payload dictionary, 'hpgauges' files are copied up to EC2
    # and then returned in the resultant ZIP S3 file
    project.payload = {}
    gauges = build_urs_boundary(project.mux_input_filename, project.event_sts)
    project.payload['hpgauges'] = gauges

    log.info('Calling: get_minmaxAOI()')
    get_minmaxAOI()

    # copy all required python modules to scripts directory
    ec2_name = os.path.join(ScriptsDir, Ec2RunTsuDATOnEC2)
    log.debug("Copying EC2 run file '%s' to scripts directory '%s'."
              % (Ec2RunTsuDAT, ec2_name))
    shutil.copy(Ec2RunTsuDAT, ec2_name)

    for extra in RequiredFiles:
        log.info('Copying %s to S3 scripts directory' % extra)
        shutil.copy(extra, ScriptsDir)

    # dump the current 'projects' object back into JSON, put in 'scripts'
    json_file = os.path.join(ScriptsDir, JsonDataFilename)
    log.info('Dumping JSON to file %s' % json_file)
    dump_json_to_file(project, json_file)
    dump_project_py()

    # bundle up the working directory, put it into S3
    zipname = ('%s-%s-%s-%s.zip'
               % (project.user, project.project,
                  project.scenario, project.setup))
    zip_tmp_dir = tempfile.mkdtemp(prefix='tsudat2_zip_')
    zippath = os.path.join(zip_tmp_dir, zipname)
    log.info('Making zip %s from %s' % (zippath, project.working_directory))
    make_dir_zip(project.working_directory, zippath)

    s3_name = os.path.join(project.InputS3DataDir, zipname)
    try:
        s3 = s3_connect()
        bucket = s3.create_bucket(project.S3Bucket)
        key = bucket.new_key(s3_name)
        log.info('Creating S3 file: %s/%s' % (project.S3Bucket, s3_name))
        key.set_contents_from_filename(zippath)
        log.info('Done!')
        key.set_acl('public-read')
    except boto.exception.S3ResponseError, e:
        log.critical('S3 error: %s' % str(e))
        print('S3 error: %s' % str(e))
        sys.exit(10)

    # clean up the local filesystem
    dir_path = os.path.join(project.working_directory, project.user)
    log.debug('Deleting work directory: %s' % dir_path)
#    shutil.rmtree(dir_path)
    log.debug('Deleting zipped S3 data: %s' % zippath)
    shutil.rmtree(zippath, ignore_errors=True)

    # WHEN WE NO LONGER NEED THE 'GETSWW' OPTION, DELETE ALL LINES: #DELETE ME
    # for now, assume ['getsww': False] if project.getsww undefined #DELETE ME
    try:                                                            #DELETE ME
        getsww = project.getsww                                     #DELETE ME
    except AttributeError:                                          #DELETE ME
        getsww = False                                              #DELETE ME

    # start the EC2 instance we are using
    user_data = {'User': project.user,
                 'Project': project.project,
                 'Scenario': project.scenario,
                 'Setup': project.setup,
                 'BaseDir': project.working_directory,
                 'Bucket': project.S3Bucket,
                 'InputS3DataDir': project.InputS3DataDir,
                 'OutputS3DataDir': project.OutputS3DataDir,
                 'AbortS3DataDir': project.AbortS3DataDir,
                 'ScriptPath': ScriptsDir,
                 'getsww': getsww,                                  #DELETE ME
                 'Debug': 'debug' if project.debug else 'production'}

    user_data = json.dumps(user_data, ensure_ascii=True, separators=(',', ':'))
    log.info('Starting AMI %s, user_data=%s' % (DefaultAmi, str(user_data)))
    try:
        instance = start_ami(DefaultAmi, user_data=user_data)
    except boto.exception.EC2ResponseError, e:
        log.critical('EC2 error: %s' % str(e))
        print('EC2 error: %s' % str(e))
        sys.exit(10)

    print('*'*80)
    print('* Started instance: %s' % instance.dns_name)
    print('*'*80)
    log.info('Started instance: %s' % instance.dns_name)

    log.debug('instance: %s' % str(dir(instance)))

    return instance
