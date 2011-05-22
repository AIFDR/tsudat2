#!/usr/bin/env python

"""
Utility to convert zone+lon_lat to easting+northing.
"""

import anuga.coordinate_transforms.redfearn as redfearn

def l_ll2en(points):
    # points = [(id,lon,lat), ...]
    result = []
    for (id,lon, lat) in points:
        (z, easting, northing) = redfearn(lat, lon)
        result.append((id, lon, lat, easting, northing))
    return result

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print('usage: %s <file>' % sys.argv[0])
        sys.exit(10)

    with open(sys.argv[1], 'r') as fp:
        lines = fp.readlines()

    lines = lines[1:]

    data = []
    for line in lines:
        (id, lon, lat) = line.strip().split(',')
        id = int(id.strip())
        lon = float(lon.strip())
        lat = float(lat.strip())
        data.append((id, lon, lat))

    new_data = l_ll2en(data)

    print('# index, longitude, latitude, easting, northing')
    for nd in new_data:
        print('%d,%.4f,%.4f,%.4f,%.4f' % nd)
