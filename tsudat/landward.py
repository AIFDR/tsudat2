#!/usr/bin/env python

"""
Sample 'landward_boundary' code.

The object of the exercise is to take a set of points defining a bounding
polygon and extract the 'landward boundary' set of points, that is, the
polygon points that are on land.  We assume that the caller can 'adorn'
each point with some sort of flag indicating if the point is on land or
sea.  Given that metadata, this code will return a canonical format list
of points that are on land (still with adornment).
"""

import unittest


def landward(points):
    """Get landward points.

    points  list of points with added land/sea flag:
                [(x,y,f),(x',y',f'),...]

    Returns a canonical 'landward' subset of points.
    Throws 'Exception' if points data is invalid.
    """

    # check polygon validity - count L->S transitions
    last = None
    count = 0
    for (_,_,f) in points:
        if last is None:
            last = f
        else:
            if last == 'l' and f == 's':
                count += 1
            last = f
    (_, _, first) = points[0]
    # handle wraparound
    if last == 'l' and first == 's':
        count += 1

    if count != 1:
        raise Exception('polygon must have exactly one set of points on land')

    # check first and last points, 4 cases: l/l, s/s, s/l, l/s
    (_, _, first) = points[0]
    (_, _, last) = points[-1]

    if first == 'l' and last == 'l':
        # sea embedded in the middle, search first 's'
        first_sea = None
        for (i, (_,_,f)) in enumerate(points):
            if f == 's':
                first_sea = i
                break
        if first_sea is None:
            raise Exception('polygon must include seaward hazard points')
        # search forward from first_sea for first 'l'
        for (i, (_,_,f)) in enumerate(points[first_sea:]):
            if f == 'l':
                first_land = i + first_sea
                break
    elif first == 's' and last == 's':
        # land embedded in the middle, search forwards for first 'l'
        first_land = None
        for (i, (_,_,f)) in enumerate(points):
            if f == 'l':
                first_land = i
                break
        if first_land is None:
            raise Exception('polygon must include points on land')
        # search forward from first_land for first 's'
        for (i, (_,_,f)) in enumerate(points[first_land:]):
            if f == 's':
                first_sea = i + first_land
                break
    elif first == 's' and last == 'l':
        # land starts after first, search forward for first 'l'
        for (i, (_,_,f)) in enumerate(points):
            if f == 'l':
                first_land = i
                break
        # first_sea is element 0
            first_sea = 0
    elif first == 'l' and last == 's':
        # sea starts after first land at 0, look for first 's'
        for (i, (_,_,f)) in enumerate(points):
            if f == 's':
                first_sea = i
                break
        # first_land  is index 0
        first_land = 0

    # pull out the bracketed land points, in order
    if first_sea > first_land:
        land = points[first_land:first_sea]
    else:
        land = points[first_land:] + points[:first_sea]

    return land


class TestLandward(unittest.TestCase):

    def test_simple_land_first(self):
        # LS case
        points = [(0,0,'l'), (1,1,'l'), (2,2,'l'),
                  (4,1,'s'), (3,0,'s'), (-1,2,'s')]
        expect = [(0,0,'l'), (1,1,'l'), (2,2,'l')]
        land = landward(points)
        self.assertEqual(land, expect)

    def test_simple_land_embedded(self):
        # SS case
        points = [(-1,2,'s'), (0,0,'l'), (1,1,'l'),
                  (2,2,'l'), (4,1,'s'), (3,0,'s')]
        expect = [(0,0,'l'), (1,1,'l'), (2,2,'l')]
        land = landward(points)
        self.assertEqual(land, expect)

    def test_simple_land_wraparound(self):
        # LL case
        points = [(2,2,'l'), (4,1,'s'), (3,0,'s'),
                  (-1,2,'s'), (0,0,'l'), (1,1,'l')]
        expect = [(0,0,'l'), (1,1,'l'), (2,2,'l')]
        land = landward(points)
        self.assertEqual(land, expect)

    def test_simple_sea_first(self):
        # SL case
        points = [(4,1,'s'), (3,0,'s'), (-1,2,'s'), (0,0,'l'), (1,1,'l'), (2,2,'l')]
        expect = [(0,0,'l'), (1,1,'l'), (2,2,'l')]
        land = landward(points)
        self.assertEqual(land, expect)

    def test_no_sea_points(self):
        points = [(0,0,'l'), (1,1,'l'), (2,2,'l'),
                  (4,1,'l'), (3,0,'l'), (-1,2,'l')]
        self.assertRaises(Exception, landward, points)

    def test_no_land_points(self):
        points = [(0,0,'s'), (1,1,'s'), (2,2,'s'),
                  (4,1,'s'), (3,0,'s'), (-1,2,'s')]
        self.assertRaises(Exception, landward, points)

    def test_two_land_extents(self):
        # SS case, 2 land extents
        points = [(-1,2,'s'), (0,0,'l'), (1,1,'s'),
                  (2,2,'l'), (4,1,'s'), (3,0,'s')]
        self.assertRaises(Exception, landward, points)


if __name__ == '__main__':
    unittest.main()

