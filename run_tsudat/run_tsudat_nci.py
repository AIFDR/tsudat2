"""
Run an ANUGA simulation on the NCI eucalyptus cloud.
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

import tsudat_log as log


log.console_logging_level = log.CRITICAL+1    # turn console logging off
log.log_logging_level = log.INFO


# the AMI we are going to run
#DefaultAmi = 'emi-DF191069'  # Ubuntu_9.10
DefaultAmi = 'emi-326E0D10'  # Ubuntu_9.10_tsudat_2.0

# keypair used to start instance
DefaultKeypair = 'tsudatkey'

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
Ec2RunTsuDAT = 'nci_run_tsudat.py'
Ec2RunTsuDATOnEC2 = 'run_tsudat.py'

# names of additional required files in S3 bucket file
RequiredFiles = ['export_depthonland_max.py',
                 'export_newstage_max.py']

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


def make_dir_zip(dirname, zipname):
    """Make a ZIP file from a directory.

    dirname  path to directory to zip up
    zipname  path to ZIP file to create
    """

    log.debug('zip -q -r %s %s' % (zipname, dirname))
    os.system('zip -q -r %s %s' % (zipname, dirname))

def make_tsudat_dir(base, user, proj, scen, setup, event, nuke=False):
    """Create a TsuDAT2 work directory.

    base        path to base of new directory structure
    user        user name
    proj        project name
    scen        scenario name
    setup       type of run ('trial', etc)
    event       event number
    nuke        optional - destroy any existing structure first (IGNORED)

    Creates a TSUDAT directory structure under the 'base' path.
    The created 'user' directory has a data+time suffix added.

    Returns a tuple of paths to places under 'base' required by the UI:
        (user_base, raw_elevation, boundaries, meshes, polygons, gauges)
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
    timestamp = time.strftime('_%Y%m%dT%H%M%S')
    run_dir = os.path.join(base, user+timestamp, proj, scen, setuu
#    if nuke:
#        shutil.rmtree(run_dir, ignore_errors=True)
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
    topographies = os.path.join(run_dir, 'topographies')

    # save scripts path globally to help run_tsudat()
    ScriptsDir = os.path.join(run_dir, 'scripts')

    # a fudge - because the zip process doesn't save empty directories
    # we must write a small file into empty directories we zip
    placeholder = os.path.join(meshes, '.placeholder')
    with open(placeholder, 'w') as fd:
        pass

    # return paths to various places under 'base'
    return (run_dir, raw_elevation, boundaries, meshes, polygons, gauges)
    #return (run_dir, raw_elevation, boundaries, meshes, polygons, gauges, topographies)

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
    log.info('# Launching simulation')
    log.info('#'*90)

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
    os.system('ls -l %s' % zip_tmp_dir)

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
#    log.debug('Deleting work directory: %s' % dir_path)
#    shutil.rmtree(dir_path)
    log.debug('Deleting zipped S3 data: %s' % zippath)
    shutil.rmtree(zippath, ignore_errors=True)

    # WHEN WE NO LONGER NEED THE 'GETSWW' OPTION, DELETE ALL LINES: #DELETE ME
    # for now, assume ['getsww': False] if project.getsww undefined #DELETE ME
    try:                                                            #DELETE ME
        getsww = project.getsww                                     #DELETE ME
    except AttributeError:                                          #DELETE ME
        getsww = False                                              #DELETE ME

    # get JSON for userdata
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

    # save user data into <work_dir>/restart
    restart_file = os.path.join(project.working_directory, '_restart_',
                                '%s_%s_%s_%s.restart'
                                % (project.user, project.project,
                                   project.scenario, project.setup))
    with open(restart_file, 'wb') as fp:
        fp.write(user_data)

    # actually start the instance
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
