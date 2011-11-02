#!/usr/bin/env python

"""
Create a colour-coded waveheight copy of o_amp_green.

usage:  make_wh_cc_hp_file.py [<path to data>]

This creates an output file very similar to o_amp_green except that wave
heights are replaced by a colout-code string.  The wave heights are mapped
over the range [0.0, 1.0.].

This is for loading TsuDATA data into the TsuDAT2 database.  Uses URSAPI.
"""


import sys
import os.path

import ursapi


# default path to data - overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

OutputFile = './wave_heights_color.txt'


def main():
    # override path to data directory if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    fd = open(OutputFile, 'w')

    lines = []

    urs_path = os.path.join(DataPath, 'earthquake_data')
    urs = ursapi.URSData(urs_path)
    hp_list = urs.get_hp()
    rp_list = urs.get_rp()

    # put lon+lat into array
    for (id, lon, lat, dep) in hp_list:
        lines.append([lon, lat, dep])

    # for each RP, add colour-coded WH to each HP row
    for rp in rp_list:
        wh_list = urs.get_hp_by_wh(rp)
        cc_list = urs.colour_code_by_wh_absolute(wh_list)
        zip_list = zip(lines, cc_list)
        for z in zip_list:
            (line, cc) = z
            (_, _, _, _, ccstr) = cc
            line.append(ccstr)

    hdr = ' ' * 33
    for rp in rp_list:
        fld = '%13d' % rp
        hdr += fld
    fd.write(hdr+'\n')

    for l in lines:
        row = '%11.4f%11.4f%11.4f' % (l[0], l[1], l[2])
        for c in l[3:]:
            row += ' %12s' % c
        fd.write(row+'\n')

    fd.close()

if __name__ == '__main__':
    main()
