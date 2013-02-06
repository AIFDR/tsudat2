"""
Create data sets which the user can download to run simulations.
"""



def run_sim_boundary(json_data, logger=None):
"""
Create  sts and csv files for the user, based on the event
    that they selected and the polygon they drew.
    
args:
    json_data:  the path to the JSON data file
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
        
    
    gauges = build_urs_boundary(project.mux_input_filename,
                                    project.event_sts)
                                    
    return gauges
