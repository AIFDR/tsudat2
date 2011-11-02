import sys
import os.path
import re
import glob

# default mount path - can be overridden by sys.argv[1]
DataPath = '/media/537510fd-c89e-442d-8be0-3163f1bbe59b/Tsu-DAT_Data'

# derived paths to file(s)
OutputFile = './event_list.csv'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')

def main():
    # override data path if sys.argv[1] supplied
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]
 
    # prepare output file
    out_fd = open(OutputFile, 'wb')
    out_fd.write('eventID,Zone,QuakeProb,Mq,Slip,NumSubfaults\n')
   
    input_mask = os.path.join(DataPath, 'earthquake_data', 'multimux', 'i_multimux-*')

    # get all files matching mask in the directory
    count = 0
    event_id = 1
    for fname in glob.glob(input_mask):
        count += 1

        # get hpID from filename
        basename = os.path.basename(fname)
        (_, zone) = basename.split('-')
	print zone

        # get data from this file
        fd = open(fname, 'r')
        lines = fd.readlines()
        fd.close()

        # get header line, split out return periods
        header = lines[0].strip()
        lines = lines[1:]

	index = 0
	while index < len(lines):
		event = lines[index].strip()
		# 4 P-flores-00000                     7.000   88.400   25.000   10.000 0.377766E-05
		(num_subfaults, event_xx, mag, area, length, width, prob) = SpacesPattern.split(event)
		# flores-0000_waveheight-z-mux2  0.884004E+00 0.128317E-04 0.700000E+01   1
		(_, slip, _, _, _) = SpacesPattern.split(lines[index+1].strip())
		out_line = '%s,%s,%s,%s,%s,%s\n' % (event_id, zone, prob, mag, slip, num_subfaults)
		print out_line
		out_fd.write(out_line)
		event_id += 1
		index += int(num_subfaults)+1

    out_fd.close()

if __name__ == '__main__':
    main()
