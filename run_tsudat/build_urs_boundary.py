"""
Replacement function that wraps the legacy function urs2sts()
and passes in the data from the EventSelection <event>.list file.
"""

import os
from Scientific.IO.NetCDF import NetCDFFile
import numpy as num

import anuga
import anuga.utilities.log as log

import project


def get_sts_gauge_data(filename, verbose=False):
    """Get gauges (timeseries of index points)."""

    log.info('get_sts_gauge_data: filename=%s' % filename)
    fid = NetCDFFile(filename+'.sts', 'r')      #Open existing file for read
    permutation = fid.variables['permutation'][:]
    x = fid.variables['x'][:] + fid.xllcorner   #x-coordinates of vertices
    y = fid.variables['y'][:] + fid.yllcorner   #y-coordinates of vertices
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
    log.info('get_sts_gauge_data: maxname=%s' % maxname)
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

    return quantities,elevation,time


def build_urs_boundary(event_file, output_dir):
    """Build a boundary STS file from a set of MUX files.

    event_file  name of mux meta-file or single mux stem
    output_dir  directory to write STS data to
    """

    # if we are using an EventSelection multi-mux file
    if project.multi_mux:
        # get the mux+weight data from the meta-file (in <boundaries>)
        mux_event_file = os.path.join(project.event_folder, event_file)
        log.info('using multi-mux file %s' % mux_event_file)
        try:
            fd = open(mux_event_file, 'r')
            mux_data = fd.readlines()
            fd.close()
        except IOError, e:
            msg = 'File %s cannot be read: %s' % (mux_event_file, str(e))
            raise Exception, msg
        except:
            raise

        # first line of file is # filenames+weight in rest of file
        num_lines = int(mux_data[0].strip())
        mux_data = mux_data[1:]
        log.info('number of sources %d' % num_lines)

        # quick sanity check on input mux meta-file
        if num_lines != len(mux_data):
            msg = ('Bad file %s: %d data lines, but line 1 count is %d'
                   % (event_file, len(mux_data), num_lines))
            raise Exception, msg

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
        log.info('creating sts file: %s' % output_dir)
        anuga.urs2sts(mux_filenames,
                basename_out=output_dir,
                ordering_filename=project.urs_order,
                weights=mux_weights,
                verbose=False)
    else:                           # a single mux stem file, assume 1.0 weight
        mux_file = os.path.join(project.event_folder, event_file)
        mux_filenames = [mux_file]
        log.info('using single-mux file %s' % mux_file)

        weight_factor = 1.0
        mux_weights = weight_factor*num.ones(len(mux_filenames), num.Float)
            
        order_filename = project.urs_order

        log.info('reading %s' % order_filename)
        # Create ordered sts file
        anuga.urs2sts(mux_filenames,
                basename_out=output_dir,
                ordering_filename=order_filename,
                weights=mux_weights,
                verbose=False)

    # report on progress so far
    sts_file = os.path.join(project.event_folder, project.scenario_name)
    quantities, elevation, time = get_sts_gauge_data(sts_file, verbose=False)
    log.info('%d %d' % (len(elevation), len(quantities['stage'][0,:])))

    

