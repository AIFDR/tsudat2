"""
Generates ascii grids of nominated areas -
Input: sww file from run_model.py
       boundaries for grids from project.py
Outputs: ascii grids of specified variables
Stored in the 'outputs_folder' folder for respective .sww file

Note:
If producing a grid for the entire extent cellsize should be greater than 30m
If producing grids for inundation area resolution should be greater than mesh (ie ~22m)
"""

import os
import sys

import anuga
import anuga.utilities.log as log

import project


def export_results_max():
    """Export maximum resuts."""

    directory = project.output_folder
    time_dirs = [os.path.basename(project.output_run)]

    # sww filename extensions ie. if batemans_bay_time_37860_0.sww, input
    # into list 37860
    # make sure numbers are in sequential order
    times = []

    # Now set the timestep at which you want the raster generated.
    # Either set the actual timestep required or use 'None' to indicate that
    # you want the maximum values in the raster over all timesteps
    timestep = None    # None means no timestep!
    #timestep = 0       # To check initial stage

    ######
    # Define allowed variable names and associated equations to generate values.
    ######
    # Note that mannings n (friction value) is taken as 0.01, as in the model
    # run density of water is 1000
    var_equations = {'stage': 'stage',
                     'momentum': '(xmomentum**2 + ymomentum**2)**0.5',
                     'depth': 'stage-elevation',
                     'speed': '(xmomentum**2 + ymomentum**2)**0.5/(stage-elevation+1.e-6)',
                     'energy': '(((xmomentum/(stage-elevation+1.e-6))**2'
                               '  + (ymomentum/(stage-elevation+1.e-6))**2)'
                               '*0.5*1000*(stage-elevation+1.e-6))+(9.81*stage*1000)',
                     'bed_shear_stress': ('(((1/(stage-elevation+1.e-6)**(7./3.))*1000*9.81*0.01**2*(xmomentum/(stage-elevation+1.e-6))*((xmomentum/(stage-elevation+1.e-6))**2+(ymomentum/(stage-elevation+1.e-6))**2)**0.5)**2'
                                          '+ ((1/(stage-elevation+1.e-6)**(7./3.))*1000*9.81*0.01**2*(ymomentum/(stage-elevation+1.e-6))*((xmomentum/(stage-elevation+1.e-6))**2+(ymomentum/(stage-elevation+1.e-6))**2)**0.5)**2)**0.5'),
                     'elevation': 'elevation'}

    ######
    # Start script, running through variables, area, folder, sww file
    # (determine by times)
    # Then creates a maximum ascii if there is more than one sww file
    ######

    for which_var in project.UI_var:
        if which_var not in var_equations:
            log.critical('Unrecognized variable name: %s' % which_var)
            break

        for which_area in project.UI_area:
            if which_area == 'All':
                easting_min = None
                easting_max = None
                northing_min = None
                northing_max = None
            else:
                try:
                    easting_min = eval('project.xmin%s' % which_area)
                    easting_max = eval('project.xmax%s' % which_area)
                    northing_min = eval('project.ymin%s' % which_area)
                    northing_max = eval('project.ymax%s' % which_area)
                except AttributeError:
                    log.critical('Unrecognized area name: %s' % which_area)
                    break

            for time_dir in time_dirs:
                names = [os.path.join(directory, time_dir,
                                      project.scenario_name)]
                for time in times:
                    names.append(os.path.join(directory, time_dir,
                                              project.scenario_name)
                                 + '_time_' + str(time) + '_0')

                asc_name = []   

                for name in names:
                    outname = name + '_' + which_area + '_' + which_var
                    quantityname = var_equations[which_var]

                    log.info('start sww2dem: time_dir=%s' % time_dir)

                    anuga.sww2dem(name+'.sww', outname+'.asc',
                                  quantity=quantityname,
                                  reduction=max,
                                  cellsize=project.UI_cell_size,      
                                  easting_min=easting_min,
                                  easting_max=easting_max,
                                  northing_min=northing_min,
                                  northing_max=northing_max,        
                                  verbose=False)

                    asc_name.append(outname + '.asc')

                if len(names) > 1:
                    maxasc_outname = (os.path.join(directory, time_dir,
                                                   project.scenario_name)
                                      +'_'+which_area+'_'+which_var+'_max.asc')

                    log.info('max asc outname=%s' % maxasc_outname)
                    log.info('asc_name: %s' % str(asc_name))

                    anuga.MaxAsc(maxasc_outname, asc_name)
                else:
                    log.info('only one sww input')
