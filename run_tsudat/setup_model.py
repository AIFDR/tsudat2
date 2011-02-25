"""
Module to check the project.py 'configuration' file, perform
sanity checks plus a quick check on mesh generation.  Returns
an 'adorned' version of the project object.

Also callable as a stand-alone program, mainly to view the results
of the mesh generation.
"""

import os

import get_multimux
import anuga
from anuga.geometry.polygon import number_mesh_triangles
import anuga.utilities.log as log

import project


def setup_model():
    """Perform sanity checks, adorn project object.

    The checks here can be simpler than for full-blown ANUGA as the directory
    structure is automatically generated.
    """

    # flag - we check many things and then don't proceed if anything wrong
    sanity_error = False               # checked at bottom of this file

    #####
    # check directory Structure
    #####

    if not os.path.exists(project.home):
        log.error("Sorry, data directory '%s' doesn't exist" % project.home)
        sanity_error = True

    if not os.path.exists(project.muxhome):
        log.error("Sorry, MUX directory '%s' doesn't exist" % project.muxhome)
        sanity_error = True

    if not os.path.exists(project.anuga_folder):
        log.error("Sorry, ANUGA directory '%s' doesn't exist"
                  % project.anuga_folder)
        sanity_error = True

    if not os.path.exists(project.topographies_folder):
        log.error("Sorry, topo directory '%s' doesn't exist"
                  % project.topographies_folder)
        sanity_error = True

    if not os.path.exists(project.polygons_folder):
        log.error("Sorry, polygon directory '%s' doesn't exist"
                  % project.polygons_folder)
        sanity_error = True

    if not os.path.exists(project.boundaries_folder):
        log.error("Sorry, boundaries directory '%s' doesn't exist"
                  % project.boundaries_folder)
        sanity_error = True

    if not os.path.exists(project.output_folder):
        log.error("Sorry, outputs directory '%s' doesn't exist"
                  % project.output_folder)
        sanity_error = True

    if not os.path.exists(project.gauges_folder):
        log.error("Sorry, gauges directory '%s' doesn't exist"
                  % project.gauges_folder)
        sanity_error = True

    if not os.path.exists(project.meshes_folder):
        log.error("Sorry, meshes directory '%s' doesn't exist"
                  % project.meshes_folder)
        sanity_error = True

    if not os.path.exists(project.mux_data_folder):
        log.error("Sorry, mux data directory '%s' doesn't exist"
                  % project.mux_data_folder)
        sanity_error = True

    # generate the event.lst file for the event
    get_multimux.get_multimux(project.event, project.multimux_folder, project.mux_input)

    # if multi_mux is True, check if multi-mux file exists
    if project.multi_mux:
        if not os.path.exists(project.mux_input):
            log.error("Sorry, MUX input file '%s' doesn't exist"
                      % project.mux_input)
            sanity_error = True

    if not os.path.exists(project.event_folder):
        log.error("Sorry, you must generate event %s with EventSelection."
                  % project.event)
        sanity_error = True

    #####
    # determine type of run
    #####

    if project.setup == 'trial':
        project.scale_factor = 100
        project.time_thinning = 96
        project.yieldstep = 240
    elif project.setup == 'basic': 
        project.scale_factor = 4
        project.time_thinning = 12
        project.yieldstep = 120
    elif project.setup == 'final': 
        project.scale_factor = 1
        project.time_thinning = 4
        project.yieldstep = 60
    else:
        log.error("Sorry, you must set the 'setup' variable to one of:"
                  '   trial - coarsest mesh, fast\n'
                  '   basic - coarse mesh\n'
                  '   final - fine mesh, slowest\n'
                  '\n'
                  "'setup' was set to '%s'" % project.setup)
        sanity_error = True

    #####
    # check for errors detected above.
    #####

    if sanity_error:
        msg = 'You must fix the above errors before continuing.'
        raise Exception(msg)

    #####
    # Reading polygons and creating interior regions
    #####

#    # Create list of land polygons with initial conditions
#    project.land_initial_conditions = []
#    for (filename, MSL) in project.land_initial_conditions_filename:
#        polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
#                                                  filename))
#        project.land_initial_conditions.append([polygon, MSL])

#    # Create list of interior polygons with scaling factor
#    project.interior_regions = []
#    for (filename, maxarea) in project.interior_regions_data:
#        polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
#                                                  filename))
#        project.interior_regions.append([polygon,
#                                         maxarea*project.scale_factor])

    # Initial bounding polygon for data clipping 
    project.bounding_polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
                                                  project.bounding_polygon_filename))
    project.bounding_maxarea = project.bounding_polygon_maxarea*project.scale_factor

    # Estimate the number of triangles                     
    trigs_min = number_mesh_triangles(project.interior_regions,
                                      project.bounding_polygon,
                                      project.bounding_maxarea)

    log.info('min estimated number of triangles=%d' % trigs_min)


################################################################################

if __name__ == '__main__':
    setup_model()
