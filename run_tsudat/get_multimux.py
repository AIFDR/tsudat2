"""A routine to write the event.lst data.

The standalone program is used to test the function.

usage: get_multimux.py <mmux_dir> <event> <output_file>
"""

import os
import re


# name of the fault name file (in multimux directory)
FaultNameFilename = 'fault_list.txt'

# match any number of spaces beteen fields
SpacesPattern = re.compile(' +')


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


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(10)

    index = 1
    mmux = sys.argv[index]; index += 1
    event = int(sys.argv[index]); index += 1
    ofile = sys.argv[index]; index += 1

    get_multimux(event, mmux, ofile)


