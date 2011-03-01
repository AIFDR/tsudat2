"""
Run an ANUGA simulation.

usage:  run_tsudat(json_data)

where 'json_data' is the path to the json data file from the UI.
"""

import os
import glob
import json
import traceback

import setup_model
import build_elevation
import build_urs_boundary
import run_model
import export_results_max
import get_timeseries

import anuga.utilities.log as log
log.console_logging_level = log.CRITICAL # turn console logging mostly off
log.log_logging_level = log.INFO

import project


# dictionary to handle attribute renaming from json->project
# 'json_name': 'ANUGA_name',
RenameDict = {'mesh_friction': 'friction',
              'smoothing': 'alpha',
              'end_time': 'finaltime',
              'layers': 'var',
              'raster_resolution': 'cell_size',
             }


def adorn_project(json_data):
    """Adorn the project object with data from the json file.

    json_data  path to the UI json datat file

    Also adds extra project attributes derived from json data.
    """


    # parse the json
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
    project.anuga_folder = os.path.join(project.home, project.user, project.project, project.scenario_name, project.setup)
    project.topographies_folder = os.path.join(project.anuga_folder, 'topographies')
    project.polygons_folder = os.path.join(project.anuga_folder, 'polygons')
    project.boundaries_folder = os.path.join(project.anuga_folder, 'boundaries')
    project.output_folder = os.path.join(project.anuga_folder, 'outputs')
    project.gauges_folder = os.path.join(project.anuga_folder, 'gauges')
    project.meshes_folder = os.path.join(project.anuga_folder, 'meshes')
    project.event_folder = project.boundaries_folder
    project.raw_elevation_folder = os.path.join(project.home, project.user,
                                                project.project,
                                                'raw_elevation')

    # MUX data files
    # Directory containing the MUX data files to be used with EventSelection.
    project.mux_data_folder = os.path.join(project.muxhome, 'mux')
    project.multimux_folder = os.path.join(project.muxhome, 'multimux')

    project.mux_input_filename = 'event_%d.lst' % project.event

    #####
    # Location of input and output data
    #####

    # The absolute pathstem of the all elevation, generated in build_elevation.py
    project.combined_elevation = os.path.join(project.topographies_folder, 'combined_elevation')

    # The absolute pathname of the mesh, generated in run_model.py
    project.meshes = os.path.join(project.meshes_folder, 'meshes.msh')

    # The pathname for the urs order points, used within build_urs_boundary.py
    project.urs_order = os.path.join(project.boundaries_folder, 'urs_order.csv')

    # The absolute pathname for the landward points of the bounding polygon,
    # Used within run_model.py)
    project.landward_boundary = os.path.join(project.boundaries_folder, 'landward_boundary.csv')

    # The absolute pathname for the .sts file, generated in build_boundary.py
    project.event_sts = project.boundaries_folder

    # The absolute pathname for the gauges file
    project.gauges = os.path.join(project.gauges_folder, 'gauges_final.csv')

    # full path to where MUX files (or meta-files) live
    project.mux_input = os.path.join(project.event_folder, 'event_%d.lst' % project.event)

    project.land_initial_conditions = []

    # if .debug isn't defined, set it to False
    try:
        project.debug
    except AttributeError:
        project.debug = False


def get_youngest_input():
    """Get date/time of youngest input file."""

    input_dirs = [project.polygons_folder, project.raw_elevation_folder]
    input_files = [project.urs_order,
                   os.path.join(project.boundaries_folder,
                                '%s.sts' % project.scenario_name),
                   project.landward_boundary]

    youngest = 0.0	# time at epoch start

    # check all files in given directories
    for dir in input_dirs:
        for file in glob.glob(os.path.join(dir, '*')):
            mtime = os.path.getmtime(file)
            youngest = max(mtime, youngest)

    # check individual files
    for file in input_files:
        mtime = os.path.getmtime(file)
        youngest = max(mtime, youngest)

    return youngest


def excepthook(type, value, tb):
    """Exception hook routine."""

    msg = '\n' + '='*80 + '\n'
    msg += 'Uncaught exception:\n'
    msg += ''.join(traceback.format_exception(type, value, tb))
    msg += '='*80 + '\n'
    log.critical(msg)


def run_tsudat(json_data):
    """"Run ANUGA using data from a json data file."""


    def dump_project_py():
        """Debug routine - dump project attributes to the log."""

        # list all project.* attributes
        for key in dir(project):
            if not key.startswith('__'):
                try:
                    log.info('project.%s=%s' % (key, eval('project.%s' % key)))
                except AttributeError:
                    pass

    # plug our exception handler into the python system
    sys.excepthook = excepthook

    # get json data and adorn project object with it's data
    adorn_project(json_data)

    # set logfile to be in run output folder
    log.log_filename = os.path.join(project.output_folder, 'tsudat.log')

    # run the tsudat simulation
    if project.debug:
        dump_project_py()

    youngest_input = get_youngest_input()
    sww_file = os.path.join(project.output_folder, project.scenario_name+'.sww')
    try:
        sww_ctime = os.path.getctime(sww_file)
    except OSError:
        sww_ctime = 0.0		# SWW file not there

    if project.force_run or youngest_input > sww_ctime:
        log.info('#'*90)
        log.info('# Running simulation')
        log.info('#'*90)
        setup_model.setup_model()
        build_elevation.build_elevation()
        build_urs_boundary.build_urs_boundary(project.mux_input_filename,
                                              project.event_sts)
        run_model.run_model()
        log.info('End of simulation')
    else:
        log.info('#'*90)
        log.info('# Not running simulation')
        log.debug('# SWW file %s is younger than input data' % sww_file)
        log.info('# If you want to force a simulation run, select FORCE RUN')
        log.info('#'*90)

    # now do optional post-run extractions
    if project.get_results_max:
       log.info('~'*90)
       log.info('~ Running max.export_results_max()')
       log.info('~'*90)
       export_results_max.export_results_max()
       log.info('export_results_max() has finished')

    if project.get_timeseries:
       log.info('~'*90)
       log.info('~ Running get_timeseries()')
       log.info('~'*90)
       get_timeseries.get_timeseries()
       log.info('get_timeseries() has finished')


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print('usage: %s <json_data>' % sys.argv[0])
        sys.exit(10)

    run_tsudat(sys.argv[1])
