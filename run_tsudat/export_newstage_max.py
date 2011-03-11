"""
Module to export the 'stage' value maximum values where depth > 0.01.

    result = stage if (stage-elevation) > 0.01 else NODATA
"""

import os
import numpy as num

from anuga.abstract_2d_finite_volumes.util import remove_lone_verts
from anuga.coordinate_transforms.geo_reference import Geo_reference
from anuga.utilities.file_utils import get_all_swwfiles
import anuga.utilities.log as log

import types
from Scientific.IO.NetCDF import NetCDFFile

import ermapper_grids


from anuga.geometry.polygon import inside_polygon, outside_polygon
from anuga.abstract_2d_finite_volumes.util import apply_expression_to_dictionary
from anuga.fit_interpolate.interpolate import Interpolate


# various default values
DEFAULT_CELLSIZE = 10
DEFAULT_BLOCK_SIZE = 10000
DEFAULT_DECIMAL_PLACES = 3
DEFAULT_NODATA = -9999
DEFAULT_DATUM = 'WGS84'


def export_newstage_max(name_in, name_out,
                        quantity=None,	# NOT USED
                        reduction=None,	# always 'max'
                        cellsize=DEFAULT_CELLSIZE,
                        number_of_decimal_places=DEFAULT_DECIMAL_PLACES,
                        NODATA_value=DEFAULT_NODATA,
                        easting_min=None,
                        easting_max=None,
                        northing_min=None,
                        northing_max=None,
                        verbose=False,	# NOT USED, but passed through
                        origin=None,
                        datum=DEFAULT_DATUM,
                        block_size=DEFAULT_BLOCK_SIZE):
    """Read SWW file and extract the maximum depth values, but only for land.

    name_in                   input filename (must be SWW)
    name_out                  output filename (.asc or .ers)
    quantity                  NOT USED
    reduction                 always 'max'
    cellsize
    number_of_decimal_places  number of decimal places for values
    NODATA_value              the value to use if NODATA
    easting_min
    easting_max
    northing_min
    northing_max
    verbose                   NOT USED, but passed through
    origin
    datum
    block_size                number of slices along non-time axis to process

    Also write accompanying file with same basename_in but extension .prj used
    to fix the UTM zone, datum, false northings and eastings.  The prj format
    is assumed to be:
        Projection    UTM
        Zone          56
        Datum         WGS84
        Zunits        NO
        Units         METERS
        Spheroid      WGS84
        Xshift        0.0000000000
        Yshift        10000000.0000000000
        Parameters
    """

    (basename_in, in_ext) = os.path.splitext(name_in)
    (basename_out, out_ext) = os.path.splitext(name_out)
    out_ext = out_ext.lower()

    if in_ext != '.sww':
        raise IOError('Input format for %s must be .sww' % name_in)

    if out_ext not in ['.asc', '.ers']:
        raise IOError('Format for %s must be either asc or ers.' % name_out)

    false_easting = 500000
    false_northing = 10000000

    assert(isinstance(block_size, (int, long, float)))

    log.debug('Reading from %s' % name_in)
    log.debug('Output directory is %s' % name_out)

    # open SWW file
    fid = NetCDFFile(name_in)

    # get extent and reference
    x = fid.variables['x'][:]
    y = fid.variables['y'][:]
    volumes = fid.variables['volumes'][:]
    times = fid.variables['time'][:]

    number_of_timesteps = fid.dimensions['number_of_timesteps']
    number_of_points = fid.dimensions['number_of_points']

    if origin is None:
        # get geo_reference since SWW files don't have to have a geo_ref
        try:
            geo_reference = Geo_reference(NetCDFObject=fid)
        except AttributeError, e:
            geo_reference = Geo_reference() # Default georef object

        xllcorner = geo_reference.get_xllcorner()
        yllcorner = geo_reference.get_yllcorner()
        zone = geo_reference.get_zone()
    else:
        zone = origin[0]
        xllcorner = origin[1]
        yllcorner = origin[2]

    # Create result array and start filling, block by block.
    result = num.zeros(number_of_points, num.float)

    log.debug('Slicing sww file, num points: %s, block size: %s'
             % (str(number_of_points), str(block_size)))

    for start_slice in xrange(0, number_of_points, block_size):
        # Limit slice size to array end if at last block
        end_slice = min(start_slice + block_size, number_of_points)

        # Get slices of all required variables
        stage = fid.variables['stage'][:,start_slice:end_slice]
        elevation = fid.variables['elevation'][start_slice:end_slice]

        # get new 'stage', but only if (stage - elevation) > 0.01
        res = num.where((stage-elevation) > 0.01, stage, NODATA_value)

        if len(res.shape) == 2:
            new_res = num.zeros(res.shape[1], num.float)
            for k in xrange(res.shape[1]):
                new_res[k] = reduction(res[:,k])
            res = new_res

        result[start_slice:end_slice] = res

    # Post condition: Now q has dimension: number_of_points
    assert len(result.shape) == 1
    assert result.shape[0] == number_of_points

    log.debug('Processed values for newstage are in [%f, %f]'
              % (min(result), max(result)))

    # Create grid and update xll/yll corner and x,y
    # Relative extent
    if easting_min is None:
        xmin = min(x)
    else:
        xmin = easting_min - xllcorner

    if easting_max is None:
        xmax = max(x)
    else:
        xmax = easting_max - xllcorner

    if northing_min is None:
        ymin = min(y)
    else:
        ymin = northing_min - yllcorner

    if northing_max is None:
        ymax = max(y)
    else:
        ymax = northing_max - yllcorner

    msg = ('xmax must be greater than or equal to xmin.  '
           'I got xmin = %f, xmax = %f' % (xmin, xmax))
    assert xmax >= xmin, msg

    msg = ('ymax must be greater than or equal to xmin.  '
           'I got ymin = %f, ymax = %f' % (ymin, ymax))
    assert ymax >= ymin, msg

    log.debug('Creating grid')
    ncols = int((xmax-xmin)/cellsize) + 1
    nrows = int((ymax-ymin)/cellsize) + 1

    # New absolute reference and coordinates
    newxllcorner = xmin + xllcorner
    newyllcorner = ymin + yllcorner

    x = x + xllcorner - newxllcorner
    y = y + yllcorner - newyllcorner

    vertex_points = num.concatenate ((x[:,num.newaxis], y[:,num.newaxis]), axis=1)
    assert len(vertex_points.shape) == 2

    grid_points = num.zeros ((ncols*nrows, 2), num.float)

    for i in xrange(nrows):
        if out_ext == '.asc':
            yg = i * cellsize
        else:
            # this will flip the order of the y values for ers
            yg = (nrows-i) * cellsize

        for j in xrange(ncols):
            xg = j * cellsize
            k = i*ncols + j

            grid_points[k, 0] = xg
            grid_points[k, 1] = yg

    # Remove loners from vertex_points, volumes here
    vertex_points, volumes = remove_lone_verts(vertex_points, volumes)
    # export_mesh_file('monkey.tsh',{'vertices':vertex_points, 'triangles':volumes})
    interp = Interpolate(vertex_points, volumes, verbose=verbose)

    log.debug('Interpolating')

    # Interpolate using quantity values
    grid_values = interp.interpolate(result, grid_points).flatten()

    log.debug('Interpolated values are in [%f, %f]'
              % (num.min(grid_values), num.max(grid_values)))

    # Assign NODATA_value to all points outside bounding polygon (from interpolation mesh)
    P = interp.mesh.get_boundary_polygon()
    outside_indices = outside_polygon(grid_points, P, closed=True)

    for i in outside_indices:
        grid_values[i] = NODATA_value

    if out_ext == '.ers':
        # setup ERS header information
        grid_values = num.reshape(grid_values, (nrows, ncols))
        header = {}
        header['datum'] = '"%s"' % datum
        # FIXME The use of hardwired UTM and zone number needs to be made optional
        # FIXME Also need an automatic test for coordinate type (i.e. EN or LL)
        header['projection'] = '"UTM-%s"' % str(zone)
        header['coordinatetype'] = 'EN'
        if header['coordinatetype'] == 'LL':
            header['longitude'] = str(newxllcorner)
            header['latitude'] = str(newyllcorner)
        elif header['coordinatetype'] == 'EN':
            header['eastings'] = str(newxllcorner)
            header['northings'] = str(newyllcorner)
        header['nullcellvalue'] = str(NODATA_value)
        header['xdimension'] = str(cellsize)
        header['ydimension'] = str(cellsize)
        header['value'] = '"depthonland"'

        log.info('Writing %s' % name_out)

        #Write the file
        ermapper_grids.write_ermapper_grid(name_out, grid_values, header)

        fid.close()
    else:
        #Write to Ascii format
        #Write prj file
        prjfile = basename_out + '.prj'

        log.info('Writing %s' % prjfile)

        prjid = open(prjfile, 'w')
        prjid.write('Projection    %s\n' % 'UTM')
        prjid.write('Zone          %d\n' % zone)
        prjid.write('Datum         %s\n' % datum)
        prjid.write('Zunits        NO\n')
        prjid.write('Units         METERS\n')
        prjid.write('Spheroid      %s\n' % datum)
        prjid.write('Xshift        %d\n' % false_easting)
        prjid.write('Yshift        %d\n' % false_northing)
        prjid.write('Parameters\n')
        prjid.close()

        log.info('Writing %s' % name_out)

        ascid = open(name_out, 'w')
        ascid.write('ncols         %d\n' % ncols)
        ascid.write('nrows         %d\n' % nrows)
        ascid.write('xllcorner     %d\n' % newxllcorner)
        ascid.write('yllcorner     %d\n' % newyllcorner)
        ascid.write('cellsize      %f\n' % cellsize)
        ascid.write('NODATA_value  %d\n' % NODATA_value)

        format = '%%.%ge' % number_of_decimal_places
        for i in range(nrows):
            if i % ((nrows+10)/10) == 0:
                log.debug('Doing row %d of %d' % (i, nrows))

            base_index = (nrows - i - 1)*ncols

            slice = grid_values[base_index:base_index+ncols]

            num.savetxt(ascid, slice.reshape(1,ncols), format, ' ' )

        ascid.close()
        fid.close()

    return basename_out
