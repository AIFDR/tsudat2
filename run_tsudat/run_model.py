"""
Run a tsunami inundation scenario for a TsuDAT scenario.

The scenario is defined by a triangular mesh created from project.polygon, the
elevation data is compiled into a pts file through build_elevation.py and a
simulated tsunami is generated through an sts file from build_boundary.py.

Input: sts file (build_boundary.py for respective event)
       pts file (build_elevation.py)
       information from project file
Outputs: sww file stored in project.output_run_time_dir 
The export_results_all.py and get_timeseries.py is reliant
on the outputs of this script

Ole Nielsen and Duncan Gray, GA - 2005, Jane Sexton, Nick Bartzis, GA - 2006
Ole Nielsen, Jane Sexton and Kristy Van Putten - 2008
Nick Horspool, GA - 2010 Modified to be compatible with Anuga 1.2.0
"""

import os
import time
from Scientific.IO.NetCDF import NetCDFFile

import anuga
import build_urs_boundary as bub
import anuga.utilities.log as log

import project


def run_model():
    """Run a tsunami simulation for a scenario."""

    log.info('@'*90)
    log.info('@ Running simulation')
    log.info('@'*90)

    # THIS IS DONE IN run_tsudat()
#    # Create the STS file
#    log.info('project.mux_data_folder=%s' % project.mux_data_folder)
#    if not os.path.exists(project.event_sts + '.sts'):
#        bub.build_urs_boundary(project.mux_input_filename, project.event_sts)

    # Read in boundary from ordered sts file
    event_sts = anuga.create_sts_boundary(project.event_sts)

    # Reading the landward defined points, this incorporates the original
    # clipping polygon minus the 100m contour
    landward_boundary = anuga.read_polygon(project.landward_boundary)

    # Combine sts polyline with landward points
    bounding_polygon_sts = event_sts + landward_boundary

    # Number of boundary segments
    num_ocean_segments = len(event_sts) - 1
    # Number of landward_boundary points
    num_land_points = anuga.file_length(project.landward_boundary)

    # Boundary tags refer to project.landward_boundary
    # 4 points equals 5 segments start at N
    boundary_tags={'back': range(num_ocean_segments+1,
                                 num_ocean_segments+num_land_points),
                   'side': [num_ocean_segments,
                            num_ocean_segments+num_land_points],
                   'ocean': range(num_ocean_segments)}

    # Build mesh and domain
    log.debug('bounding_polygon_sts=%s' % str(bounding_polygon_sts))
    log.debug('boundary_tags=%s' % str(boundary_tags))
    log.debug('project.bounding_maxarea=%s' % str(project.bounding_maxarea))
    log.debug('project.interior_regions=%s' % str(project.interior_regions))
    log.debug('project.meshes=%s' % str(project.meshes))

    domain = anuga.create_domain_from_regions(bounding_polygon_sts,
                                boundary_tags=boundary_tags,
                                maximum_triangle_area=project.bounding_maxarea,
                                interior_regions=project.interior_regions,
                                mesh_filename=project.meshes,
                                use_cache=False,
                                verbose=False)

    domain.geo_reference.zone = project.zone
    log.info('\n%s' % domain.statistics())

    domain.set_name(project.scenario_name)
    domain.set_datadir(project.output_folder) 
    domain.set_minimum_storable_height(0.01)  # Don't store depth less than 1cm

    # Set the initial stage in the offcoast region only
    if project.land_initial_conditions:
        IC = anuga.Polygon_function(project.land_initial_conditions,
                                    default=project.tide,
                                    geo_reference=domain.geo_reference)
    else:
        IC = 0
    domain.set_quantity('stage', IC, use_cache=True, verbose=False)
    domain.set_quantity('friction', project.friction) 
    domain.set_quantity('elevation', 
                        filename=project.combined_elevation+'.pts',
                        use_cache=True, verbose=False, alpha=project.alpha)

    # Setup boundary conditions 
    log.debug('Set boundary - available tags: %s' % domain.get_boundary_tags())

    Br = anuga.Reflective_boundary(domain)
    Bt = anuga.Transmissive_stage_zero_momentum_boundary(domain)
    Bd = anuga.Dirichlet_boundary([project.tide, 0, 0])
    Bf = anuga.Field_boundary(project.event_sts+'.sts',
                        domain, mean_stage=project.tide, time_thinning=1,
                        default_boundary=anuga.Dirichlet_boundary([0, 0, 0]),
                        boundary_polygon=bounding_polygon_sts,
                        use_cache=True, verbose=False)

    domain.set_boundary({'back': Br,
                         'side': Bt,
                         'ocean': Bf}) 

    # Evolve system through time
    t0 = time.time()
    for t in domain.evolve(yieldstep=project.yieldstep, 
                           finaltime=project.finaltime,
                           skip_initial_step=False): 
        log.info('\n%s' % domain.timestepping_statistics())
        log.info('\n%s' % domain.boundary_statistics(tags='ocean'))

    log.info('Simulation took %.2f seconds' % (time.time()-t0))

################################################################################

if __name__ == '__main__':
    run_model()
