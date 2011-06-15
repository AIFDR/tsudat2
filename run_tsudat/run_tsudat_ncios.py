"""
Run an ANUGA simulation on an NCI OpenStack worker.
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
import subprocess
import boto

import messaging_amqp as msg
import tsudat_log as logger


logger.console_logging_level = logger.CRITICAL+1    # turn console logging off
logger.log_logging_level = logger.INFO


# HUGE BIG FUDGE
PathToRunTsudat = '/data/httpd/default/tsudat2/run_tsudat'

# the AMI of the instance to run, and associated metadata
DefaultAMI = 'ami-00000038'     # Ubuntu_10.04_Tsudat_2.0.26
DefaultKeypair = 'testkey'
DefaultType = 'c1.large'

# path to the mounted common filesystem
#CommonFileSystem = os.path.join(os.sep, 'data', 'tsudat_runs')
CommonFileSystem = os.path.join(os.sep, 'data', 'run_tsudat')

# dictionary to handle attribute renaming from JSON->project
# format: {'UI_name': 'ANUGA_name', ...}
RenameDict = {'mesh_friction': 'friction',
              'smoothing': 'alpha',
              'end_time': 'finaltime',
              'layers': 'var',
              'raster_resolution': 'cell_size',
              'elevation_data_list': 'point_filenames',
             }

# various default values
DefaultURSOrderFile = 'urs_order.csv'

# define defaults for various things
# used by default_project_values()
# format: iterable of (<name>, <default value>)
DefaultJSONValues = (('urs_order_file', DefaultURSOrderFile),
                    )


# name of run_tsudat() file, here and on worker (name change)
Ec2RunTsuDAT = 'ncios_run_tsudat.py'
Ec2RunTsuDATOnEC2 = 'run_tsudat.py'

# names of additional required files in input-data directory
RequiredFiles = ['export_depthonland_max.py', 'export_newstage_max.py',
                 'messaging_amqp.py']

# name of the JSON data file
JsonDataFilename = 'data.json'

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


def make_tsudat_dir(base, user, proj, scen, setup, event, nuke=False):
    """Create a TsuDAT2 work directory.

    base        path to base of new directory structure (eg, /tmp/tsudat)
    user        user name
    proj        project name
    scen        scenario name
    setup       type of run ('trial', etc)
    event       event number
    nuke        optional - destroy any existing structure first (IGNORED)

    Creates a TSUDAT directory structure under the 'base' path.
    The created 'user' directory has a data+time suffix added.

    Returns a tuple of paths to places under 'base' required by the UI:
        (user_base, raw_elevation, boundaries, meshes, polygons,
         gauges, topographies, user_dir)
    """

    global ScriptsDir

    print('base=%s' % str(base))
    print('user=%s' % str(user))
    print('proj=%s' % str(proj))
    print('scen=%s' % str(scen))
    print('setup=%s' % str(setup))

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
    timestamp = time.strftime('_%Y%m%dT%H%M%S')
    user_dir = os.path.join(base, user+timestamp)
    run_dir = os.path.join(user_dir, proj, scen, setup)
    makedirs_noerror(run_dir)
    print('made: %s' % str(run_dir))

    # create the 'raw_elevation' directory for a project
    raw_elevation = os.path.join(base, user+timestamp, proj, 'raw_elevation')
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
    topographies = os.path.join(run_dir, 'topographies')

    # save scripts path globally to help run_tsudat()
    ScriptsDir = os.path.join(run_dir, 'scripts')

    # make all directories writable by everybody
    cmd = 'chmod -R a+rw %s' % user_dir
    print(cmd)
    os.system(cmd)

    # return paths to various places under 'base'
    return (run_dir, raw_elevation, boundaries, meshes, polygons,
            gauges, topographies, user_dir)

def send_message(message):
    """Send a message to the worker(s).

    message  JSON string
    """

    msg.post_worker_message(project.user, project.project, project.scenario,
                            project.setup, message=message)

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
        print('setting project attribute %s to %s' % (new_key, value))
        project.__setattr__(new_key, value)

    # set default values for attributes that aren't defined or not provided
    define_default('mesh_file', '%s.msh' % project.scenario)

    define_default('debug', True)
    define_default('force_run', True)

    # add extra derived attributes
    # paths to various directories
    project.run_directory = os.path.join(project.user_directory,
                                         project.project, project.scenario,
                                         project.setup)
    project.anuga_folder = project.run_directory
    project.topographies_folder = os.path.join(project.anuga_folder,
                                               'topographies')
    project.polygons_folder = os.path.join(project.anuga_folder, 'polygons')
    project.boundaries_folder = os.path.join(project.anuga_folder, 'boundaries')
    project.output_folder = os.path.join(project.anuga_folder, 'outputs')
    project.gauges_folder = os.path.join(project.anuga_folder, 'gauges')
    project.meshes_folder = os.path.join(project.anuga_folder, 'meshes')
    project.event_folder = project.boundaries_folder
    project.raw_elevation_directory = os.path.join(project.working_directory,
                                                   project.user_directory,
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

#    # The complete path to the elevation, generated in build_elevation()
#    if project.combined_elevation_file:
#        project.combined_elevation_file = os.path.join(
#                                              project.topographies_folder,
#                                              project.combined_elevation_file)

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

    project    the project object to dump
    json_file  the file to dump JSON to

    Dump all 'non-special' attributes of the object.
    """

    ui_dict = {}
    for attr_name in dir(project):
        if not attr_name.startswith('_'):
            ui_dict[attr_name] = project.__getattribute__(attr_name)
     
    with open(json_file, 'w') as fd:
        json.dump(ui_dict, fd, indent=2, separators=(',', ':'))

def default_project_values():
    """Default certain values if they don't appear in the project object."""

    for (name, value) in DefaultJSONValues:
        if getattr(project, name, None) is None:
#            if name == 'urs_order_file':
#                value = os.path.join(project.user_directory, project.project,
#                                     project.scenario, project.setup)
            setattr(project, name, value)

    project.sts_filestem = project.scenario

def start_ami(ami, key_name=DefaultKeypair, instance_type=DefaultType,
              user_data=None):
    """Start the configured AMI, wait until it's running.

    ami            the ami ID ('ami-????????')
    key_name       the keypair name
    instance_type  type of instance to run
    user_data      the user data string to pass to instance
    """

    if user_data is None:
        user_data = ''

    # write user data to a file
    (fd, userdata_file) = tempfile.mkstemp(prefix='tsudat_userdata_', text=True)
    os.write(fd, user_data)
    os.close(fd)
    print('write user_data file: %s' % userdata_file)
    print('user_data=%s' % str(user_data))

    cmd = ('. /root/.nova/novarc; /usr/bin/euca-run-instances %s -k %s -t %s -f %s'
           % (ami, key_name, instance_type, userdata_file))
    log.debug('Doing: %s' % cmd)
    log.debug('user_data: %s' % user_data)
    print('Doing: %s' % cmd)
    print('user_data: %s' % user_data)
    retcode = os.system(cmd)
    log.debug('retcode=%d' % retcode)
    print('retcode=%d' % retcode)


def run_tsudat(json_data):
    """Run ANUGA on an NCI OpenStack worker.

    json_data  the path to the JSON data file
    """

    # plug our exception handler into the python system
    sys.excepthook = excepthook

    # get JSON data and adorn project object with its data
    adorn_project(json_data)

    # default certain values if not supplied in JSON data
    default_project_values()

    # set logfile to be in run output folder

    log_filename = os.path.join(project.output_folder, 'ui.log')
    global log
    if project.debug:
        log = logger.Log(logfile=log_filename, level=logger.DEBUG)
        dump_project_py()
    else:
        print('log filename=%s' % log_filename)
        log = logger.Log(logfile=log_filename)

    # do all required data generation before EC2 run
    log.info('#'*90)
    log.info('# Launching simulation')
    log.info('#'*90)

    # copy all required python modules to scripts directory
    ec2_name = os.path.join(ScriptsDir, Ec2RunTsuDATOnEC2)
    src_name = os.path.join(PathToRunTsudat, Ec2RunTsuDAT)
    log.debug("Copying worker run file '%s' to scripts directory '%s'."
              % (src_name, ec2_name))
    print("Copying worker run file '%s' to scripts directory '%s'."
          % (src_name, ec2_name))
    shutil.copy(src_name, ec2_name)

    for extra in RequiredFiles:
        src_name = os.path.join(PathToRunTsudat, extra)
        log.info('Copying %s to %s' % (src_name, ScriptsDir))
        shutil.copy(src_name, ScriptsDir)

    # dump the current 'projects' object back into JSON, put in 'scripts'
    json_file = os.path.join(ScriptsDir, JsonDataFilename)
    log.info('Dumping JSON to file %s' % json_file)
    dump_json_to_file(project, json_file)
    dump_project_py()

#    # move the work directory to common filesystem with worker
#    source_dir = project.user_directory.split(os.sep)[-1]
#    source = project.user_directory
#    destination = os.path.join(CommonFileSystem, source_dir)
#    if destination != source:
#        log.debug('mv %s %s' % (source, destination))
#        print('mv %s %s' % (source, destination))
#        shutil.move(source, destination)

    # WHEN WE NO LONGER NEED THE 'GETSWW' OPTION, DELETE ALL LINES: #DELETE ME
    # for now, assume ['getsww': False] if project.getsww undefined #DELETE ME
    try:                                                            #DELETE ME
        getsww = project.getsww                                     #DELETE ME
    except AttributeError:                                          #DELETE ME
        getsww = False                                              #DELETE ME

    # get JSON for worker
    message = {'User': project.user,
               'UserDir': project.user_directory,
               'Project': project.project,
               'Scenario': project.scenario,
               'Setup': project.setup,
               'BaseDir': project.run_directory,
               'ScriptPath': ScriptsDir,
               'JSONData': os.path.join(ScriptsDir, JsonDataFilename),
               'getsww': getsww,                                    #DELETE ME
               'Debug': 'debug' if project.debug else 'production'}

    user_data = json.dumps(message, ensure_ascii=True, separators=(',', ':'))

    # save user data into <work_dir>/restart
    restart_dir = os.path.join(project.working_directory, '_restart_')
    try:
        os.makedirs(restart_dir)
    except OSError:
        pass            # ignore error if directory exists
    restart_file = os.path.join(restart_dir,
                                '%s_%s_%s_%s.restart'
                                % (project.user, project.project,
                                   project.scenario, project.setup))
    with open(restart_file, 'wb') as fp:
        fp.write(user_data)

    # now start a worker
    log.info('Starting worker, user_data=%s' % str(user_data))
    start_ami(DefaultAMI, user_data=user_data)
    log.info('Started instance')
