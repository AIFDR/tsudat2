"""
Build the urs boundary.
"""

import sys
import os
import anuga
import re
import tempfile
import zipfile
import ntpath

# name of the fault name file (in multimux directory)
FaultNameFilename = 'fault_list.txt'

# match any number of spaces between fields
SpacesPattern = re.compile(' +')


def create_urs_order(landward_boundary_path, interior_hazard_points_path,
                     urs_order_path):
    """Create the urs order file.
    
    Uses landward boundary data (LB) and interior hazard points data (iHP).
        1. Read LB data
        2. Read iHP data
        3. Get last LB point
        4. Get distance from last LB to first and last iHP
        5. if last LB closer to last iHP, invert iHP order
        6. write iHP to urs order file

        args:
            landward_boundary_path: the location of the landward_boundary file
            interior_hazard_points_path: location of the interior_hazard_points
                                         file
            urs_order_path: Where the urs order file will be written.
    """

    # get landward boundary data: lb_data = [(e,n), ...]
    with open(landward_boundary_path, 'r') as fp:
        lines = fp.readlines()
    lb_data = []
    for line in lines:
        (e, n) = line.split(',')
        e = float(e.strip())
        n = float(n.strip())
        lb_data.append((e, n))

    # get interior HP data: hp_data = [(e,n), ...]
    with open(interior_hazard_points_path, 'r') as fp:
        lines = fp.readlines()
    hp_data = []
    for line in lines:
        (hp_id, lon, lat, e, n) = line.split(',')
        hp_id = int(hp_id.strip())
        lon = float(lon.strip())
        lat = float(lat.strip())
        e = float(e.strip())
        n = float(n.strip())
        hp_data.append((e, n, hp_id, lon, lat))

    # get last LB and first and last iHP, get distances (squared)
    (last_lb_x, last_lb_y) = lb_data[-1]
    (first_hp_x, first_hp_y, _, _, _) = hp_data[0]
    (last_hp_x, last_hp_y, _, _, _) = hp_data[-1]
    d2_first = (first_hp_x-last_lb_x)**2 + (first_hp_y-last_lb_y)**2
    d2_last = (last_hp_x-last_lb_x)**2 + (last_hp_y-last_lb_y)**2

    # if distance to last < distance to first invert hp_data list
    if d2_last < d2_first:
        hp_data.reverse()

    # now create urs_order file

    with open(urs_order_path, 'wb') as fp:
        fp.write('index,longitude,latitude\n')
        for (_, _, hp_id, lon, lat) in hp_data:
            fp.write('%d,%f,%f\n' % (hp_id, lon, lat))


def get_deformation(mux_event_file, deformation_folder, ouput_file):
    
    """
    Function to take list of mux files and generate a txt file of
    surface deformation for input into build_deformation

    Input: event.lst file
    Output: path to deformation txt file
    """

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

    def_ext = '-180c.grd' # extension of deformation file
    def_filenames = []
    for line in mux_data:
        muxname = line.strip().split()[0]
        sf_name = muxname.split('_')[0]
        defname = sf_name + def_ext
        defname = os.path.join(deformation_folder, defname)
        def_filenames.append(defname)

    slip_weights = [float(line.strip().split()[1]) for line in mux_data]

    f = tempfile.NamedTemporaryFile(suffix='.grd', 
                                    prefix='bldurs_get_deformation',
                                    delete=False)
    f.close()
    grd_file = f.name
    

    # create GMT call
    if len(def_filenames) == 1:
        gmtcmd = "grdmath " + def_filenames[0] + " " + str(slip_weights[0]) \
            + " MUL = " + grd_file
    else:
        gmtcmd = "grdmath " + def_filenames[0] + " " + str(slip_weights[0]) \
            + " MUL "
        for i in range(1,len(def_filenames)):
            gmtcmd = gmtcmd + def_filenames[i] + " " + str(slip_weights[i]) \
                + " MUL ADD "

        gmtcmd = gmtcmd + " = " + grd_file

    # convert from grd to xyz
    gmtcmd2 = 'grd2xyz %s > %s' % (grd_file, ouput_file)

    print '----GMT GRDMATHD---------'
    print gmtcmd
    print '----GMT GRD2XYZ----------'
    os.system(gmtcmd)
    print gmtcmd2
    os.system(gmtcmd2)  
    
    os.remove(grd_file)

    return ouput_file

def get_multimux(event, multimux_dir, output_file):
    """Does exactly what David Burbidge's 'get_multimux' program does.

    event         event ID
    multimux_dir  path to the multimux files
    output_file   The event file
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
                event_info_raw = infd.readline()
            except IOError:
                raise Exception("Error reading file %s: EOF reading event"
                                % mmx_filename)

            if not event_info_raw:
                break
            #nsubfault = int(nsubfault)
            event_info = SpacesPattern.split(event_info_raw, maxsplit=4)
            nsubfault = int(event_info[1])

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

    
def build_urs_boundary(mux_event_file, sts_outputfile, urs_order_file, 
                       mux_data_folder):
    """Build a boundary STS file from a set of MUX files.

    mux_event_file  name of mux meta-file or single mux stem or event file
    output_dir  directory to write STS data to
    urs_order_file: The urs order file
    mux_data_folder: The directory where the mux data is

    Returns a list of generated 'sts_gauge' files.
    """

    # Assuming EventSelection multi-mux file
    #the mux+weight data from the meta-file (in <boundaries>)
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
        muxname_long = line.strip().split()[0]
        muxbasename = muxname_long.split('-z-mux2')[0]
        #print "muxbasename",muxbasename 
        #split_index = muxname.index('.grd')
        #muxname = muxname[:split_index+len('.grd')]
        muxname = os.path.join(mux_data_folder, muxbasename)
        mux_filenames.append(muxname)

    mux_weights = [float(line.strip().split()[1]) for line in mux_data]

    # Call legacy function to create STS file.
    anuga.urs2sts(mux_filenames, basename_out=sts_outputfile,
                  ordering_filename=urs_order_file,
                  weights=mux_weights, verbose=False)
                  

    #(quantities, elevation,
    # time, gen_files) = get_sts_gauge_data(sts_file, verbose=False)
    #log.debug('%d %d' % (len(elevation), len(quantities['stage'][0,:])))

    #return gen_files
    

def build_boundary_deformation(landward_boundary_path, 
                               interior_hazard_points_path,
                               event, 
                               mux_data_folder, 
                               deformation_folder, 
                               zip_filename):
    """
    Given data files written from the tsudat database, create the sts
    and deformation files.
    """
    # create temp files
    # urs_order
    f = tempfile.NamedTemporaryFile(suffix='.txt', 
                                        prefix='urs_order_path',
                                        delete=False)
    f.close()
    urs_order_path = f.name
    
    # event_file
    f = tempfile.NamedTemporaryFile(suffix='.txt', 
                                        prefix='event_file',
                                        delete=False)
    f.close()
    event_file = f.name
    
    # sts_file
    f = tempfile.NamedTemporaryFile(suffix='.sts', 
                                        prefix='sts_file_',
                                        delete=False)
    f.close()
    sts_outputfile = f.name
    
    # deformation_ouput_file
    f = tempfile.NamedTemporaryFile(suffix='.txt', 
                                        prefix='def_file_stem',
                                        delete=False)
    f.close()
    deformation_ouput_file = f.name
    
    
    create_urs_order(landward_boundary_path, interior_hazard_points_path,
                     urs_order_path)
    get_multimux(event, mux_data_folder, event_file)  
       
    #build_urs_boundary(event_file, sts_outputfile, urs_order_path, 
     #                  mux_data_folder) 
     
    get_deformation(event_file, 
                    deformation_folder, 
                    deformation_ouput_file)
    
    archive_list = [sts_outputfile, deformation_ouput_file]
    arcname_list = ['boundary_' + str(event) + '.sts',
    'deformation_' + str(event) + '.txt']
    zip_files(archive_list, arcname_list, zip_filename)
    
    os.remove(urs_order_path)
    os.remove(event_file)
    os.remove(sts_outputfile)
    os.remove(deformation_ouput_file)
    

def zip_files(archive_list=[], arcname_list=None, zfilename='default.zip'):
    if arcname_list == None:
        arcname_list = archive_list
        
    #print zfilename
    zout = zipfile.ZipFile(zfilename, "w", zipfile.ZIP_DEFLATED)
    for fname, arcname  in zip(archive_list, arcname_list):
        zout.write(fname, arcname)
    zout.close()
