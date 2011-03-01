"""
Run an ANUGA simulation.

usage:  run_tsudat(json_data)

where 'json_data' is the path to the json data file from the UI.
"""

import os
import re
import shutil
import glob
import time
import json
import traceback
from Scientific.IO.NetCDF import NetCDFFile
import numpy as num

import anuga
from anuga.geometry.polygon import number_mesh_triangles
import build_urs_boundary as bub
import anuga.utilities.log as log
log.console_logging_level = log.CRITICAL	# turn console logging off
#log.log_logging_level = log.INFO
log.log_logging_level = log.DEBUG

import project


# name of the fault name file (in multimux directory)
FaultNameFilename = 'fault_list.txt'

# match any number of spaces beteen fields
SpacesPattern = re.compile(' +')

# dictionary to handle attribute renaming from json->project
# 'json_name': 'ANUGA_name',
RenameDict = {'mesh_friction': 'friction',
              'smoothing': 'alpha',
              'end_time': 'finaltime',
              'layers': 'var',
              'raster_resolution': 'cell_size',
             }

# major directories under user/project/scenario/setup base directory
MajorSubDirs = ['topographies', 'polygons', 'boundaries', 'outputs',
                'gauges', 'meshes']


#def touch(path):
#    """Do a 'touch' for a file.
#
#    This is NOT a good solution, it's just to show where files will go."""
#
#    with file(path, 'a'):
#        os.utime(path, None)


def mk_tsudat_dir(base, user, proj, scen, setup, event):
    """Create a TsuDAT2 run directory.

    base   path to base of new directory structure
    user   user name
    proj   project name
    scen   scenario name
    setup  type of run ('trial', etc)
    event  event number

    Creates a TSUDAT directory structure under the 'base' path.

    Returns a tuple of paths to places under 'base' required by the UI:
        (raw_elevation, bondaries, meshes, polygons)
    """

    # delete any dir that might be there
    shutil.rmtree(base, ignore_errors=True)

    # create the 'raw_elevation' directory for a project
    path = os.path.join(base, user, proj, 'raw_elevation')
    raw_elevation = path
    os.makedirs(path)
#    touch(os.path.join(path, 'raw_elevation1.asc'))	# NOT IN FINAL
#    touch(os.path.join(path, 'raw_elevation2.asc'))	# NOT IN FINAL

    # create base directory after deleting any dir that might be there
    run_dir = os.path.join(base, user, proj, scen, setup)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)

    # now create major sub-dirs under $setup
    for sd in MajorSubDirs:
        os.makedirs(os.path.join(run_dir, sd))

    # get return paths
    boundaries = os.path.join(run_dir, 'boundaries')
    meshes = os.path.join(run_dir, 'meshes')
    polygons = os.path.join(run_dir, 'polygons')

#    # now create lower directories & files (NOT IN FINAL)
#    path = os.path.join(run_dir, 'topographies')
#    touch(os.path.join(path, 'combined_elevation.pts'))
#    touch(os.path.join(path, 'combined_elevation.txt'))
#
#    # NOT IN FINAL
#    path = os.path.join(run_dir, 'boundaries')
#    touch(os.path.join(path, 'event_%d.lst' % event))
#    touch(os.path.join(path, 'landward_boundary.csv'))
#    touch(os.path.join(path, 'urs_order.csv'))
#
#    # NOT IN FINAL
#    path = os.path.join(run_dir, 'outputs')
#    touch(os.path.join(path, 'generated_files'))
#
#    # NOT IN FINAL
#    path = os.path.join(run_dir, 'gauges')
#    touch(os.path.join(path, 'gauges_final.csv'))
#
#    # NOT IN FINAL
#    path = os.path.join(run_dir, 'meshes')
#    touch(os.path.join(path, 'meshes.msh'))

    # return paths to various places under 'base'
    return (raw_elevation, boundaries, meshes, polygons)


def setup_model():
    """Perform sanity checks.

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
    get_multimux(project.event, project.multimux_folder, project.mux_input)

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

    # Create list of interior polygons with scaling factor
    project.interior_regions = []
    for (filename, maxarea) in project.interior_regions_data:
        polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
                                                  filename))
        project.interior_regions.append([polygon,
                                         maxarea*project.scale_factor])

    # Initial bounding polygon for data clipping 
    project.bounding_polygon = anuga.read_polygon(os.path.join(project.polygons_folder,
                                                  project.bounding_polygon))
    project.bounding_maxarea = project.bounding_polygon_maxarea*project.scale_factor

    # Estimate the number of triangles                     
    log.debug('number_mesh_triangles(%s, %s, %s)'
              % (str(project.interior_regions),
                 str(project.bounding_polygon),
                 str(project.bounding_maxarea)))
    triangle_min = number_mesh_triangles(project.interior_regions,
                                         project.bounding_polygon,
                                         project.bounding_maxarea)

    log.info('minimum estimated number of triangles=%d' % triangle_min)


def get_multimux(event, multimux_dir, output_file):
    """Does exactly what David Burbidge's 'get_multimux' program does.

    event         event ID
    multimux_dir  path to the multimux files
    output_file   path to file to write
    """

    # get data
    filename = os.path.join(multimux_dir, FaultNameFilename)
    try:
        fd = open(filename, "r")
        fault_names = [ fn.strip() for fn in fd.readlines() ]
        fd.close()
    except IOError, msg:
        raise RuntimeError(1, "Error reading file: %s" % msg)

    # open the output file
    try:
        outfd = open(output_file, "w")
    except IOError, msg:
        raise Exception('Error opening output file: %s' % msg)

    # handle each fault
    nquake = 0
    for fn in fault_names:
        # create the filename for the multimux data file
        mmx_filename = 'i_multimux-%s' % fn
        mmx_filename = os.path.join(multimux_dir, mmx_filename)

        # Read all data in file, checking as we go
        try:
            infd = open(mmx_filename, "r")
        except IOError, msg:
            raise Exception('Error opening file: %s' % msg)

        # check fault name in file is as expected
        mux_faultname = infd.readline().strip()
        if mux_faultname != fn:
            raise Exception("Error in file %s: fault name in file isn't %s"
                            % (mmx_filename, fn))

        # read data
        while True:
            # get number of subfaults, EOF means finished
            try:
                nsubfault = infd.readline()
            except IOError:
                raise Exception("Error reading file %s: EOF reading event"
                                % mmx_filename)

            if not nsubfault:
                break
            nsubfault = int(nsubfault)

            nquake += 1
            if nquake == event:
                outfd.write(' %d\n' % nsubfault)
                for i in range(nsubfault):
                    line = infd.readline()
                    (subfaultname, slip, prob, mag, _) = \
                                   SpacesPattern.split(line, maxsplit=4)
                    subfaultname = subfaultname.strip()
                    slip = float(slip)
                    outfd.write(" %s %g\n" % (subfaultname, slip))
            else:
                for i in range(nsubfault):
                    try:
                        infd.readline()
                    except IOError:
                        raise Exception("Something wrong at bottom of file %s"
                                        % mux_faultname)

        infd.close()
    outfd.close()


def build_elevation():
    """Create combined elevation data.

    Combine all raw elevation data and clip to bounding polygon.
    """

    # Create Geospatial data from ASCII files
    geospatial_data = {}
    for filename in project.ascii_grid_filenames:
        log.info('Reading elevation file %s' % filename)
        absolute_filename = os.path.join(project.raw_elevation_folder, filename)
        anuga.asc2dem(absolute_filename+'.asc',
                      use_cache=False, verbose=False)
        anuga.dem2pts(absolute_filename+'.dem', use_cache=False, verbose=False)

        G_grid = anuga.geospatial_data.\
                     Geospatial_data(file_name=absolute_filename+'.pts',
                                     verbose=False)

        geospatial_data[filename] = G_grid.clip(project.bounding_polygon)

    # Create Geospatial data from TXT files
    for filename in project.point_filenames:
        log.info('Reading elevation file %s' % filename)
        absolute_filename = os.path.join(project.raw_elevation_folder, filename)
        G_points = anuga.geospatial_data.\
                       Geospatial_data(file_name=absolute_filename,
                                       verbose=False)

        geospatial_data[filename] = G_points.clip(project.bounding_polygon)

    #####
    # Combine, clip and export dataset 
    #####

    G = None
    for key in geospatial_data:
        G += geospatial_data[key]

    G.export_points_file(project.combined_elevation + '.pts')

    # Use for comparision in ARC
    G.export_points_file(project.combined_elevation + '.txt')


def get_sts_gauge_data(filename, verbose=False):
    """Get gauges (timeseries of index points)."""

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

    return (quantities, elevation, time)


def build_urs_boundary(event_file, output_dir):
    """Build a boundary STS file from a set of MUX files.

    event_file  name of mux meta-file or single mux stem
    output_dir  directory to write STS data to
    """

    # if we are using an EventSelection multi-mux file
    if project.multi_mux:
        # get the mux+weight data from the meta-file (in <boundaries>)
        mux_event_file = os.path.join(project.event_folder, event_file)
        try:
            fd = open(mux_event_file, 'r')
            mux_data = fd.readlines()
            fd.close()
        except IOError, e:
            msg = 'File %s cannot be read: %s' % (mux_event_file, str(e))
            raise Exception(msg)
        except:
            raise

        # first line of file is # filenames+weight in rest of file
        num_lines = int(mux_data[0].strip())
        mux_data = mux_data[1:]

        # quick sanity check on input mux meta-file
        if num_lines != len(mux_data):
            msg = ('Bad file %s: %d data lines, but line 1 count is %d'
                   % (event_file, len(mux_data), num_lines))
            raise Exception(msg)

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
        anuga.urs2sts(mux_filenames,
                basename_out=output_dir,
                ordering_filename=project.urs_order,
                weights=mux_weights,
                verbose=False)
    else:                           # a single mux stem file, assume 1.0 weight
        log.info('using single-mux file %s' % mux_file)

        mux_file = os.path.join(project.event_folder, event_file)
        mux_filenames = [mux_file]

        weight_factor = 1.0
        mux_weights = weight_factor*num.ones(len(mux_filenames), num.Float)
            
        order_filename = project.urs_order

        # Create ordered sts file
        anuga.urs2sts(mux_filenames,
                basename_out=output_dir,
                ordering_filename=order_filename,
                weights=mux_weights,
                verbose=False)

    # report on progress so far
    sts_file = os.path.join(project.event_folder, project.scenario_name)
    log.info('URS boundary filee=%s' % sts_file)

    (quantities, elevation, time) = get_sts_gauge_data(sts_file, verbose=False)
    log.debug('%d %d' % (len(elevation), len(quantities['stage'][0,:])))


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


def adorn_project(json_data):
    """Adorn the project object with data from the json file.

    json_data  path to the UI json datat file

    Also adds extra project attributes derived from json data.
    """


    # parse the json
    with open(json_data, 'r') as fp:
        ui_dict = json.load(fp)

    # adorn project object with entries from ui_dict
    for (key, value) in ui_dict.iteritems():
        # convert to str (ANUGA can't handle unicode yet)
        key = str(key)
        if isinstance(value, basestring):
            value = str(value)

        # allow renaming of attributes here
        new_key = RenameDict.get(key, key)

        # set new attribute in project object
        project.__setattr__(new_key, value)

    # add extra derived attributes
    # paths to various directories
    project.anuga_folder = os.path.join(project.home, project.user, project.project, project.scenario_name, project.setup)
    project.topographies_folder = os.path.join(project.anuga_folder, 'topographies')
    project.polygons_folder = os.path.join(project.anuga_folder, 'polygons')
    project.boundaries_folder = os.path.join(project.anuga_folder, 'boundaries')
    project.output_folder = os.path.join(project.anuga_folder, 'outputs')
    project.gauges_folder = os.path.join(project.anuga_folder, 'gauges')
    project.meshes_folder = os.path.join(project.anuga_folder, 'meshes')
    project.event_folder = project.boundaries_folder
    project.raw_elevation_folder = os.path.join(project.home, project.user,
                                                project.project,
                                                'raw_elevation')

    # MUX data files
    # Directory containing the MUX data files to be used with EventSelection.
    project.mux_data_folder = os.path.join(project.muxhome, 'mux')
    project.multimux_folder = os.path.join(project.muxhome, 'multimux')

    project.mux_input_filename = 'event_%d.lst' % project.event

    #####
    # Location of input and output data
    #####

    # The absolute pathstem of the all elevation, generated in build_elevation.py
    project.combined_elevation = os.path.join(project.topographies_folder, 'combined_elevation')

    # The absolute pathname of the mesh, generated in run_model.py
    project.meshes = os.path.join(project.meshes_folder, 'meshes.msh')

    # The pathname for the urs order points, used within build_urs_boundary.py
    project.urs_order = os.path.join(project.boundaries_folder, 'urs_order.csv')

    # The absolute pathname for the landward points of the bounding polygon,
    # Used within run_model.py)
    project.landward_boundary = os.path.join(project.boundaries_folder, 'landward_boundary.csv')

    # The absolute pathname for the .sts file, generated in build_boundary.py
    project.event_sts = project.boundaries_folder

    # The absolute pathname for the gauges file
    project.gauges = os.path.join(project.gauges_folder, 'gauges_final.csv')

    # full path to where MUX files (or meta-files) live
    project.mux_input = os.path.join(project.event_folder, 'event_%d.lst' % project.event)

    project.land_initial_conditions = []

    # if .debug isn't defined, set it to False
    try:
        project.debug
    except AttributeError:
        project.debug = False


def get_youngest_input():
    """Get date/time of youngest input file."""

    input_dirs = [project.polygons_folder, project.raw_elevation_folder]
    input_files = [project.urs_order,
                   os.path.join(project.boundaries_folder,
                                '%s.sts' % project.scenario_name),
                   project.landward_boundary]

    youngest = 0.0	# time at epoch start

    # check all files in given directories
    for dir in input_dirs:
        for file in glob.glob(os.path.join(dir, '*')):
            mtime = os.path.getmtime(file)
            youngest = max(mtime, youngest)

    # check individual files
    for file in input_files:
        mtime = os.path.getmtime(file)
        youngest = max(mtime, youngest)

    return youngest


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


def get_timeseries():
    """Get time series data."""

    name = os.path.join(project.output_folder, project.scenario_name+'.sww')
    log.debug('get_timeseries: input SWW file=%s' % name)
    log.debug('get_timeseries: gauge file=%s' % project.gauges)
    anuga.sww2csv_gauges(name, project.gauges, quantities=project.var,
                         verbose=False) 


def excepthook(type, value, tb):
    """Exception hook routine."""

    msg = '\n' + '='*80 + '\n'
    msg += 'Uncaught exception:\n'
    msg += ''.join(traceback.format_exception(type, value, tb))
    msg += '='*80 + '\n'
    log.critical(msg)


def run_tsudat(json_data):
    """"Run ANUGA using data from a json data file."""


    def dump_project_py():
        """Debug routine - dump project attributes to the log."""

        # list all project.* attributes
        for key in dir(project):
            if not key.startswith('__'):
                try:
                    log.info('project.%s=%s' % (key, eval('project.%s' % key)))
                except AttributeError:
                    pass

    # plug our exception handler into the python system
    sys.excepthook = excepthook

    # get json data and adorn project object with it's data
    adorn_project(json_data)

    # set logfile to be in run output folder
    log.log_filename = os.path.join(project.output_folder, 'tsudat.log')

    # run the tsudat simulation
    if project.debug:
        dump_project_py()

    youngest_input = get_youngest_input()
    sww_file = os.path.join(project.output_folder, project.scenario_name+'.sww')
    try:
        sww_ctime = os.path.getctime(sww_file)
    except OSError:
        sww_ctime = 0.0		# SWW file not there

    if project.force_run or youngest_input > sww_ctime:
        log.info('#'*90)
        log.info('# Running simulation')
        log.info('#'*90)
        setup_model()
        build_elevation()
        build_urs_boundary(project.mux_input_filename, project.event_sts)
        run_model()
        log.info('End of simulation')
    else:
        log.info('#'*90)
        log.info('# Not running simulation')
        log.debug('# SWW file %s is younger than input data' % sww_file)
        log.info('# If you want to force a simulation run, select FORCE RUN')
        log.info('#'*90)

    # now do optional post-run extractions
    if project.get_results_max:
       log.info('~'*90)
       log.info('~ Running export_results_max()')
       log.info('~'*90)
       export_results_max()
       log.info('export_results_max() has finished')
    else:
       log.info('~'*90)
       log.info('~ Not running export_results_max() - not requested')
       log.info('~'*90)

    if project.get_timeseries:
       log.info('~'*90)
       log.info('~ Running get_timeseries()')
       log.info('~'*90)
       get_timeseries()
       log.info('get_timeseries() has finished')
    else:
       log.info('~'*90)
       log.info('~ Not running get_timeseries() - not requested')
       log.info('~'*90)

    log.info('#'*90)
    log.info('# Simulation finished')
    log.info('#'*90)

################################################################################

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print('usage: %s <json_data>' % sys.argv[0])
        sys.exit(10)

    run_tsudat(sys.argv[1])
