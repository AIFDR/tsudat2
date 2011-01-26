import sys, traceback
from django.contrib.gis.geos import *
from django.core.exceptions import ObjectDoesNotExist
import re

from tsudat2.tsudat.models import *

sys.path.append("../")

def load_hazard_points():
    hp_file = open('../data/hazard.points', 'r')
    for line in hp_file.readlines():
        parts = line.strip().split(' ')
        lon = float(parts[0])
        lat = float(parts[1])
        id = int(parts[2])
        print lon, lat, id
        pnt = Point(lon, lat, srid=4326)
        hp = HazardPoint(tsudat_id=id, geom=pnt)
        hp.save()

def load_source_zones():
    sz_file = open('../data/zone_subfault.txt')
    for line in sz_file.readlines():
        parts = line.strip().split(' ')
        name = parts[0]
        id = int(parts[1])
        print id, name
        sz = SourceZone(tsudat_id=id, name=name)
        sz.save()

def load_subfaults():
    sf_file = open('../data/subfaults.txt')
    for line in sf_file.readlines():
        parts = line.strip().split(' ') 
        lon = float(parts[0])
        lat = float(parts[1])
        id = int(parts[2])
        sz = SourceZone.objects.get(name=parts[3])
        pnt = Point(lon, lat, srid=4326)
        sf = SubFault(tsudat_id=id, source_zone=sz, geom=pnt)
        sf.save()

def load_sz_geom():
    # This doesnt work because there are often 2 or more sets of 'lines' of sub-fault points
    szs = SourceZone.objects.all()
    for sz in szs:
        sfs = SubFault.objects.filter(source_zone=sz).order_by('tsudat_id')
        coords = [] 
        for sf in sfs:
            coords.append((sf.geom.coords[0], sf.geom.coords[1]))
        ls = LineString(coords) 
        sz.geom = ls 
        sz.save()

def load_events():
    events_file = open('../data/event_list.csv') 
    count = 0
    for line in events_file.readlines():
        if(count != 0):
            parts = line.strip().split(',')
            id = int(parts[0])
            sz = SourceZone.objects.get(name=parts[1])
            prob = float(parts[2])
            mag = float(parts[3])
            slip = float(parts[4])
            num_sf = int(parts[5])
            print id, sz, prob, mag, slip, num_sf
        count += 1

def load_wave_heights(file):
    if(file == 'color'):
        wave_heights_file = open('../data/wave_heights_color.txt')
    elif(file == 'values'):
        wave_heights_file = open('../data/wave_heights_values.txt')
    else:
        print "Invalid file type"
        return
    SpacesPattern = re.compile(' +')
    count = 0
    for line in wave_heights_file.readlines():
        if(count != 0):
            parts = SpacesPattern.split(line.strip()) 
            lon = float(parts[0])
            lat = float(parts[1])
        count += 1
        try:
            hp = HazardPoint.objects.get(tsudat_id = count-2)
            assert(lon == hp.geom.coords[0])
            assert(lat == hp.geom.coords[1])
            print hp.tsudat_id, lon, lat, hp.geom.coords[0], hp.geom.coords[1]
            index = 3
            for rp in RETURN_PERIOD_CHOICES:
                rp_val = int(rp[0])
                try:
                    hpd = HazardPointDetail.objects.get(hazard_point = hp, return_period=rp_val)
                except:
                    hpd = HazardPointDetail(hazard_point = hp, return_period = rp_val)
                if(file == 'color'):
                    hpd.color = parts[index] 
                elif(file == 'values'):
                    hpd.wave_height = float(parts[index])
                hpd.save()
                index += 1
        except ObjectDoesNotExist:
            # The loaded Hazard Points are 'thinned'
            # So every record in the wave_heights file
            # May not be in the HazardPoints file
            pass
        except:
            traceback.print_exc(file=sys.stdout) 
            pass

#load_hazard_points()
#load_source_zones()
#load_subfaults()
#load_sz_geom()
load_events()
#load_wave_heights('values')
#load_wave_heights('color')
