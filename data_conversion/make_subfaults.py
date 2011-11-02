import re

SpacesPattern = re.compile(' +')

zsf_file = open('/data/indo_ptha/earthquake_data/hazmap_files/zone_subfault.txt')
inv_file = open('/data/indo_ptha/earthquake_data/Tfiles/i_invall')

zones = []
for line in zsf_file.readlines():
	z = line.strip().split(' ')
	zone = {'name': z[0], 'index': int(z[1])}
	zones.append(zone)

inv_file_index = 0
zone_index = 0
subfaults_file = open('subfaults.txt', 'w')
for line in inv_file.readlines():
	if inv_file_index < 3:
		# Skip the first 3 lines
		pass
	else:
		parts = SpacesPattern.split(line.strip())
		line_str = str('%s %s %s %s\n' % (parts[0], parts[1], inv_file_index-3, zones[zone_index]['name']))
		subfaults_file.write(line_str)
		try:
			# 2 is slightly confusing here??
			if inv_file_index-2 == zones[zone_index+1]['index']:
				zone_index += 1
		except:
			pass
	inv_file_index += 1

subfaults_file.close()
