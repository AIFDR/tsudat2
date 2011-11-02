num_tfiles = 153 # Get a count for this rather than hardcoding

zsf_file = open('/data/indo_ptha/earthquake_data/hazmap_files/zone_subfault.txt')
zsf_list = []
for line in zsf_file.readlines():
	zsf_list.append(line.strip().split(' ')[0])
for i in range(num_tfiles):
	tfile_name = 'T-%04d' % i
	print tfile_name
	tfile = open('/data/indo_ptha/earthquake_data/Tfiles/' + tfile_name, 'w')
	header = False
	for zsf in zsf_list:
		zsf_tfile_name = '/data/indo_ptha/earthquake_data/precursor_tfiles/%s/%s' % (zsf, tfile_name)
		zsf_tfile = open(zsf_tfile_name)
		if header == False:
			header = (zsf_tfile.readline())
			tfile.write(header)
			header = True
		count = 0
		for tfile_line in zsf_tfile.readlines():
			if count > 0:
				tfile.write(tfile_line)
			count += 1
	tfile.close()
