"""
Run an ANUGA simulation.

Data received from TsuDAT2 UI through project.py.
This may change, but for now ...
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


################################################################################

if __name__ == '__main__':
    import sys

    def excepthook(type, value, tb):
        """Application exception hook routine."""

        msg = '\n' + '='*80 + '\n'
        msg += 'Uncaught exception:\n'
        msg += ''.join(traceback.format_exception(type, value, tb))
        msg += '='*80 + '\n'
        log.critical(msg)
        sys.exit(1)

    def dump_project_py():
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

