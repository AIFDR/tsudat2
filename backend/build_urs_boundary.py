"""
Build the urs boundary.
"""

import sys
import os
#import anuga


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


def get_deformation(mux_event_file, deformation_folder, ouput_stem):
    
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

    grd_file = ouput_stem + ".grd"
    txt_file = ouput_stem + ".txt"

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
    gmtcmd2 = 'grd2xyz %s > %s' % (grd_file,txt_file)

    print '----GMT GRDMATHD---------'
    print gmtcmd
    print '----GMT GRD2XYZ----------'
    os.system(gmtcmd)
    print gmtcmd2
    os.system(gmtcmd2)  

    return txt_file

