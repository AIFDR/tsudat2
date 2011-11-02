#!/usr/bin/env python

"""The API to extract data from the URS dataset."""


import os.path
import re

import util


# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


class URSData(object):
    """Object representing one URS dataset."""

    HazMapDirName = 'hazmap_files'
    MultimuxDirName = 'multimux'
    MuxDirName = 'mux'
    TfilesDirName = 'Tfiles'

    OAmpGreenFile = os.path.join(HazMapDirName, 'hazard_maps', 'o_amp_green')
    T00000File = os.path.join(TfilesDirName, 'T-0000')


    def __init__(self, urs_path):
        """Instantiate a URS dataset object.

        urs_path  path to a URS dataset directory
        """

        # check that the directory actually exists!
        crash = not os.path.isdir(urs_path)

        # check directory for files/dirs that must exist
        for subdir in (self.HazMapDirName, self.MultimuxDirName,
                       self.MuxDirName, self.TfilesDirName):
            if not crash:
                crash = not os.path.isdir(os.path.join(urs_path, subdir))

        # may want to check for some required files

        # bomb out if we got an error
        if crash:
            msg = '%s is not a URS dataset directory' % urs_path
            raise Exception(msg)

        self.urs_path = urs_path

        # set cached mapping dictionaries to None (forces build on first use)
        self.eventid_2_subfaults = None

    def get_rp(self):
        """Getlist of all allowed RP values."""

        # open o_amp_green file, if it's there
        try:
            fd = open(os.path.join(self.urs_path, self.OAmpGreenFile), 'r')
        except IOError, e:
            msg = '%s is not a URS dataset directory\n%s' % (self.urs_path, str(e))
            raise Exception(msg)

        # get single header line
        hdr = fd.readline().strip()
        rp_list = map(float, SpacesPattern.split(hdr))
        rp_list = map(int, rp_list)

        return rp_list

    def get_hp(self):
        """Get all HPs defined in dataset.

        Returns a list of tuples: (id, lon, lat).
        Get this from the o_amp_green file.  HP IDs start at 0.
        """

        # open o_amp_green file, if it's there
        try:
            fd = open(os.path.join(self.urs_path, self.OAmpGreenFile), 'r')
        except IOError, e:
            msg = '%s is not a URS dataset directory\n%s' % (self.urs_path, str(e))
            raise Exception(msg)

        # get data in file, drop single header line
        lines = fd.readlines()
        lines = lines[1:]
        fd.close()

        # step through lines, get columns 0+1+2 (lon,lat,depth) and index
        result = []
        for (id, line) in enumerate(lines):
            cols = map(float, SpacesPattern.split(line.strip())[:3])
            r = [id]
            r.extend(cols)
            result.append(tuple(r))

        return result

    def get_hp_by_wh(self, rp):
        """Get all HPs defined in dataset incuding WH for given RP.

        rp  RP for which we want HP+wave height.

        Returns a list of tuples: (id, lon, lat, depth, wh).
        HP IDs start at 0.
        """

        # open o_amp_green file, if it's there
        try:
            fd = open(os.path.join(self.urs_path, self.OAmpGreenFile), 'r')
        except IOError, e:
            msg = '%s is not a URS dataset directory\n%s' % (urs_path, str(e))
            raise Exception(msg)

        # get data in file, drop single header line
        lines = fd.readlines()
        header = lines[0]
        lines = lines[1:]
        fd.close()

        # get return periods from header line and compute WH column
        hdr_rp = map(float, SpacesPattern.split(header.strip()))
        hdr_rp = map(int, hdr_rp)

        # check that RP supplied is in allowed RPs
        if rp not in hdr_rp:
            msg = 'Return period %d not in allowed values:\n%s' % (rp, str(hdr_rp))
            raise Exception(msg)

        # get RP column, first 3 are lon, lat, depth
        rp_index = hdr_rp.index(rp) + 3

        # step through lines, get columns 0+1+2 (lon,lat,depth) and WH by computed index
        result = []
        for (hp_id, line) in enumerate(lines):
            cols = SpacesPattern.split(line.strip())
            lonlatdep = map(float, cols[:3])
            hp_id = [hp_id]
            hp_id.extend(lonlatdep)
            hp_id.append(float(cols[rp_index]))
            result.append(tuple(hp_id))

        return result

    def colour_code_by_wh_absolute(self, t):
        """Colour-code HP list by WH absolute, WH range is [0,10].

        t  list of tuples (id, lon, lat, wh)

        Return list of tuples as above but with 'wh' replaced by a colour
        string of the form #RRGGBB with each two chars a hex value. For
        example, '#00FF00' would be green.

        Colour-coding is performed over the absolute range 0 <-> 10.0.
        """

        return [(id, lon, lat, dep, util.colour_code_val(0, wh, 10.0))
                for (id, lon, lat, dep, wh) in t]

    def colour_code_by_wh_range(self, t):
        """Colour-code HP list by WH over data range.

        t  list of tuples (id, lon, lat, wh)

        Return list of tuples as above but with 'wh' replaced by a colour
        string of the form #RRGGBB with each two chars a hex value. For
        example, '#00FF00' would be green.

        Colour-coding is performed over the data range min <-> max.
        """

        min_val = min([wh for (_, _, _, _, wh) in t])
        max_val = max([wh for (_, _, _, _, wh) in t])

        return [(id, lon, lat, dep, util.colour_code_val(min_val, wh, max_val))
                for (id, lon, lat, dep, wh) in t]

    def eventid2subfaultid(self, eventid):
        """Get a list of subfault IDs for an event.

        eventid  ID of the event

        Returns a list of subfault IDs.
        """

        if not self.eventid_2_subfaults:
            # haven't got cached dictionary, try to open the file, get data
            try:
                fd = open(os.path.join(self.urs_path, self.T00000File), 'r')
            except IOError, e:
                msg = '%s is not a URS dataset directory\n%s' % (self.urs_path, str(e))
                raise Exception(msg)
            lines = fd.readlines()
            fd.close()

            # trash the first line
            lines = lines[1:]

            # load into dictionary
            self.eventid_2_subfaults = {}
            repat = re.compile(' +')        # split on one or more spaces
            for (i, l) in enumerate(lines):
                l = l.strip()
                (_, _, _, _, _, subfaults) = repat.split(l, maxsplit=5)
                subfaults = repat.split(subfaults)
                self.eventid_2_subfaults[i+1] = map(int, subfaults)

        try:
            result = self.eventid_2_subfaults[eventid]
        except KeyError:
            msg = ('Internal Error: Got invalid event ID (%d) in '
                   'URSData.eventid2subfaultid()?' % eventid)
            raise Exception(msg)

        return result


