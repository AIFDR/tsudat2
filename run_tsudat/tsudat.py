"""
Run an ANUGA simulation.

usage:  run_tsudat(json_data)

where 'json_data' is the path to the jsaon data file from the UI.
"""

import setup_model
import build_elevation
import build_urs_boundary
import run_model
import export_results_max
import get_timeseries

import anuga.utilities.log as log
log.console_logging_level = log.CRITICAL+30	# turn console logging off
log.log_logging_level = log.DEBUG

import project

def adorn_project(json_data):
    """Adorn the project object with data from json file."""

    # parse the json
    with open(json_data, 'r') as fp:
        ui_dict = json.load(fp)

    # adorn project object with entries from ui_dict
    for (key, value) in ui_dict.iteritems():
        project.__setattr__(key, value)


def excepthook(type, value, tb):
    """Exception hook routine."""

    msg = '\n' + '='*80 + '\n'
    msg += 'Uncaught exception:\n'
    msg += ''.join(traceback.format_exception(type, value, tb))
    msg += '='*80 + '\n'
    log.critical(msg)
    #sys.exit(1)


def run_tsudat(json_data):
    """"Run ANUGA using data from the json data file."""


    def dump_project_py():
        """Debug routine - dump project attributes to the log."""

        log.info('#'*90)
        log.info('#'*90)
        # list all project.* attributes
        for key in dir(project):
            if not key.startswith('__'):
                log.info('project.%s=%s' % (key, eval('project.%s' % key)))
        log.info('#'*90)
        log.info('#'*90)

    # plug our exception handler into the python system
    sys.excepthook = excepthook

    # get json data and adorn project object with it's data
    adorn_project(json_data)

    # run the tsudat simulation
    dump_project_py()

    setup_model.setup_model()
    build_elevation.build_elevation()
    build_urs_boundary.build_urs_boundary(project.mux_input_filename,
                                          project.event_sts)
    run_model.run_model()

    # now do optional post-run extractions
    if project.UI_get_results_max:
       log.info('~'*90)
       log.info('~'*90)
       export_results_max.export_results_max()

    if project.UI_get_timeseries:
       log.info('~'*90)
       log.info('~'*90)
       get_timeseries.get_timeseries()


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print('usage: %s <json_data>' % sys.argv[0])
        sys.exit(10)

    run_tsudat(sys.argv[1])
