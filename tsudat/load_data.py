import os, sys, traceback
import re
import dircache
import shutil

sys.path.append(".")
sys.path.append("../")
sys.path.append("../../")
os.environ['DJANGO_SETTINGS_MODULE'] = "tsudat2.settings"

from django.contrib.gis.geos import *
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.contrib.gis.utils import LayerMapping

from tsudat2.tsudat.models import *

DataPath = "../data/"

def load_hazard_points():
    hp_file = open(os.path.join(DataPath, 'hazard_points.txt'), 'r')
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
    sz_file = open(os.path.join(DataPath, 'zone_subfault.txt'), 'r')
    for line in sz_file.readlines():
        parts = line.strip().split(' ')
        name = parts[0]
        id = int(parts[1])
        print id, name
        sz = SourceZone(tsudat_id=id, name=name)
        sz.save()

def load_subfaults():
    sf_file = open(os.path.join(DataPath, 'subfaults.txt'), 'r')
    for line in sf_file.readlines():
        parts = line.strip().split(' ') 
        lon = float(parts[0])
        if(lon > 180):
            lon = lon - 260
        print lon
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
    events_file = open(os.path.join(DataPath, 'event_list.csv'), 'r')
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
            event = Event(tsudat_id = id,
                    source_zone = sz,
                    probability = prob,
                    magnitude = mag,
                    slip = slip)
            event.save()
        count += 1

def load_event_subfaults():
    event_sub_fault_file = open(os.path.join(DataPath, 'event_subfaults.csv'), 'r')
    for line in event_sub_fault_file.readlines():
        print line.strip()
        parts = line.strip().split(',')
        event = Event.objects.get(tsudat_id=int(parts[0]))
        sub_faults = parts[1:]
        for sf in sub_faults: 
            sf = SubFault.objects.get(tsudat_id=int(sf))
            event.sub_faults.add(sf)
        event.save()

@transaction.commit_manually
def load_subfault_detail():
    subfault_detail_file = open(os.path.join(DataPath, 'hp_rp_fid_cc.csv'), 'r')
    counter = index = count = 0
    finished_hps = []
    thinned_hps = []
    valid_hps = [] 
    sflt_id_mapping = {}
    hp_id_mapping = {}
    
    cursor = connection.cursor()
   
    current_hp_id = None

    finished = SubFaultDetail.objects.values('hazard_point').distinct()
    for x in finished:
        hp = HazardPoint.objects.get(id=x['hazard_point'])
        finished_hps.append(hp.tsudat_id) 
  
    print finished_hps 

    for line in subfault_detail_file.xreadlines():
        parts = line.strip().split(',')
        #print parts
        try:
            hp_tsudat_id = int(parts[0])
            if not hp_tsudat_id in thinned_hps and not hp_tsudat_id in finished_hps:
                if not hp_tsudat_id in valid_hps:
                    hp = HazardPoint.objects.get(tsudat_id=hp_tsudat_id)
                    hp_id_mapping[hp_tsudat_id] = hp.id 
                    valid_hps.append(hp_tsudat_id)
                sflt_tsudat_id = int(parts[2])
                if(sflt_tsudat_id in sflt_id_mapping):
                    sflt = sflt_id_mapping[sflt_tsudat_id]
                else:
                    sflt = SubFault.objects.get(tsudat_id=int(parts[2]))
                    sflt_id_mapping[sflt_tsudat_id] = sflt.id
                    sflt = None
                rp = float(parts[1])
                contribution = float(parts[3])
                sql ="insert into tsudat_subfaultdetail (hazard_point_id, sub_fault_id, return_period, contribution) VALUES (%i, %i, %f, %f)" % (hp_id_mapping[hp_tsudat_id], sflt_id_mapping[sflt_tsudat_id], rp, contribution)
                print sql
                cursor.execute(sql)
                if(hp_tsudat_id != current_hp_id):
                    print "Committing Hazard Point %s" % (hp_tsudat_id)
                    transaction.commit()
                    current_hp_id = hp_tsudat_id
                count += 1
        except ObjectDoesNotExist:
            # Hazard Points are 'thinned'
            thinned_hps.append(int(parts[0]))
            #print thinned_hps
        counter += 1
        index += 1
        if(counter >= 100):
            print "%s (%s)" % (index, count)
            counter = 0

@transaction.commit_manually
def load_event_wave_heights():
    event_wave_heights_file = open(os.path.join(DataPath, 'event_hp_wh.csv'), 'r')
    counter = index = count = 0
    finished_hps = []
    thinned_hps = []
    valid_hps = [] 
    event_id_mapping = {}
    hp_id_mapping = {}
    
    cursor = connection.cursor()
   
    current_hp_id = None

    finished = EventWaveHeight.objects.values('hazard_point').distinct()
    for x in finished:
        hp = HazardPoint.objects.get(id=x['hazard_point'])
        finished_hps.append(hp.tsudat_id) 

    for line in event_wave_heights_file.xreadlines():
        parts = line.strip().split(',')
        try:
            hp_tsudat_id = int(parts[1])
            if not hp_tsudat_id in thinned_hps and not hp_tsudat_id in finished_hps:
                if not hp_tsudat_id in valid_hps:
                    hp = HazardPoint.objects.get(tsudat_id=hp_tsudat_id)
                    hp_id_mapping[hp_tsudat_id] = hp.id 
                    valid_hps.append(hp_tsudat_id)
                event_tsudat_id = int(parts[0])
                if(event_tsudat_id in event_id_mapping):
                    event = event_id_mapping[event_tsudat_id]
                else:
                    event = Event.objects.get(tsudat_id=int(parts[0]))
                    event_id_mapping[event_tsudat_id] = event.id
                    event = None
                wh = float(parts[2])
                sql ="insert into tsudat_eventwaveheight (hazard_point_id, event_id, wave_height) VALUES (%i, %i, %f)" % (hp_id_mapping[hp_tsudat_id], event_id_mapping[event_tsudat_id], wh)
                print sql
                cursor.execute(sql)
                if(hp_tsudat_id != current_hp_id):
                    print "Committing Hazard Point %s" % (hp_tsudat_id)
                    transaction.commit()
                    current_hp_id = hp_tsudat_id
                count += 1
        except ObjectDoesNotExist:
            # Hazard Points are 'thinned'
            thinned_hps.append(int(parts[1]))
            #print thinned_hps
        counter += 1
        index += 1
        if(counter >= 100):
            print "%s (%s)" % (index, count)
            counter = 0

def load_wave_heights(file):
    if(file == 'color'):
        wave_heights_file = open(os.path.join(DataPath, 'wave_heights_color.txt'), 'r')
    elif(file == 'values'):
        wave_heights_file = open(os.path.join(DataPath, 'wave_heights_values.txt'), 'r')
    else:
        print "Invalid file type"
        return
    SpacesPattern = re.compile(' +')
    count = 0
    for line in wave_heights_file.readlines():
        if(count != 0):
            parts = SpacesPattern.split(line.strip()) 
            print parts
            lon = float(parts[0])
            lat = float(parts[1])
        count += 1
        try:
            hp = HazardPoint.objects.get(tsudat_id = count-2)
            #print hp.geom.coords[0], lon
            #assert(lon == hp.geom.coords[0])
            #print hp.geom.coords[1], lat
            #assert(lat == hp.geom.coords[1])
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

def rename_wh_rp_graphs():
    base_dir = '/var/www/tsudat2/media/wh_rp_hazard_graphs'
    list = dircache.listdir(base_dir)
    for x in list:
        print x
        lon = x[:7]
        lat = x[8:15]
        if(lat.endswith('.')):
            lat = lat[:-1]
        pnt = Point(float(lon), float(lat), srid=4326)        
        hp = HazardPoint.objects.distance(pnt).order_by('distance')[:1][0]
        src = '%s/%s' % (base_dir, x)
        dst = '%s/new/%d.png' % (base_dir, hp.tsudat_id)
        shutil.copyfile(src, dst)

def load_buildings():
    # For Nexis Data
    mapping = {
        'objectid' : 'OBJECTID',
        'longitude' : 'LONGITUDE',
        'latitude' : 'LATITUDE',
        'lid' : 'LID',
        'address' : 'ADDRESS',
        'suburb' : 'SUBURB',
        'state' : 'STATE',
        'postcode' : 'POSTCODE',
        'feature_na' : 'FEATURE_NA',
        'nexis_cad_field' : 'NEXIS_CAD_',
        'mb_code' : 'MB_CODE',
        'cd_code' : 'CD_CODE',
        'sla_code' : 'SLA_CODE',
        'lga_code' : 'LGA_CODE',
        'sd_code' : 'SD_CODE',
        'nexis_year' : 'NEXIS_YEAR',
        'nexis_use' : 'NEXIS_USE',
        'nexis_bloc' : 'NEXIS_BLOC',
        'nexis_foot' : 'NEXIS_FOOT',
        'nexis_floo' : 'NEXIS_FLOO',
        'nexis_cons' : 'NEXIS_CONS',
        'nexis_roof' : 'NEXIS_ROOF',
        'wall_type' : 'WALL_TYPE',
        'nexis_no_o' : 'NEXIS_NO_O',
        'str_value' : 'STR_VALUE',
        'cont_value' : 'CONT_VALUE',
        'nexis_peop' : 'NEXIS_PEOP',
        'nexis_inco' : 'NEXIS_INCO',
        'near_fid' : 'NEAR_FID',
        'shore_dist' : 'SHORE_DIST',
        'geom' : 'POINT'}
    lm = LayerMapping(Building, '/var/www/tsudat2/data/nexis/nexis_batemans.shp', mapping)
    lm.save(verbose=True)

def main():
    if len(sys.argv) > 1:
        global DataPath
        DataPath = sys.argv[1]

    #load_hazard_points()
    #load_source_zones()
    #load_subfaults()
    #load_sz_geom()
    #load_events()
    #load_event_subfaults()
    #load_wave_heights('values')
    #load_wave_heights('color')
    #load_event_wave_heights()
    #load_subfault_detail()
    #rename_wh_rp_graphs()
    #load_buildings()
    
if __name__ == '__main__':
    main()
