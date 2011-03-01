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

    name = os.path.join(project.output_folder, project.scenario_name+'.sww')
    log.debug('get_timeseries: input SWW file=%s' % name)
    log.debug('get_timeseries: gauge file=%s' % project.gauges)
    anuga.sww2csv_gauges(name, project.gauges, quantities=project.var,
                         verbose=False) 

