"""
Generate time series of nominated "gauges".
Input: sww file from run_model.py
       gauges project.gauge_filename
Output: csv files stage,speed,depth,elevation over time
Stored in the 'outputs_dir' folder for respective .sww file

Note:
Can run different sww files at the same time
If there is a second sww file then it is placed into a folder called sww2
Can run different gauges at the same time - ie testing boundary index point
"""

import os

import anuga
import anuga.utilities.log as log

import project


def get_timeseries():
    """Get time series data."""

    directory = project.output_folder
    time_dirs = [os.path.basename(project.output_run)]

    for time_dir in time_dirs:
        name = os.path.join(directory, time_dir, project.scenario_name)
        gauge = project.gauges
        log.critical('get_timeseries: %s  %s' % (name, gauge))
        anuga.sww2csv_gauges(name+'.sww', gauge,
                             quantities=project.UI_var, verbose=False)


