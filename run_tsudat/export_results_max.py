"""
Generates ascii grids of nominated areas -
Input: sww file from run_model.py
       boundaries for grids from project.py
Output: ascii grids of specified variables

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
    # Start script, running through variables, area, sww file
    ######

    for which_var in project.var:
        log.debug("Using value '%s'" % which_var)

        if which_var not in var_equations:
            log.critical('Unrecognized variable name: %s' % which_var)
            break

        for which_area in project.area:
            log.debug("Using area'%s'" % which_area)

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

            name = os.path.join(project.output_folder, project.scenario_name)

            outname = name + '_' + which_area + '_' + which_var
            quantityname = var_equations[which_var]

            log.debug('Generating output file: %s' % (outname+'.asc'))

            anuga.sww2dem(name+'.sww', outname+'.asc',
                          quantity=quantityname,
                          reduction=max,
                          cellsize=project.cell_size,      
                          easting_min=easting_min,
                          easting_max=easting_max,
                          northing_min=northing_min,
                          northing_max=northing_max,        
                          verbose=False)


