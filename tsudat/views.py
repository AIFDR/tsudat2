import sys, traceback
import simplejson
import geojson

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt, csrf_response_exempt
from django.core.exceptions import ObjectDoesNotExist

from vectorformats.Formats import Django, GeoJSON

from geonode.maps.models import *

from tsudat.models import *
from tsudat.tasks import run_tsudat_simulation

geoj = GeoJSON.GeoJSON()

def index(request):
    return render_to_response('tsudat/index.html')

def return_period(request):
    if not "wh" in request.GET: 
        return HttpResponse('Wave Height must be specified', status=400) 
    elif not "whd" in request.GET: 
        return HttpResponse('Wave Height Delta must be specified', status=400) 
    elif not "hp" in request.GET: 
        return HttpResponse('Hazard Point must be specified', status=400)
    else:
        try:
            hp = HazardPoint.objects.get(tsudat_id=int(request.GET.get('hp')))
        except:
            return HttpResponse('Invalid Hazard Point', status=400) 
        try:
            wh = float(request.GET.get('wh'))
            whd = float(request.GET.get('whd'))
            hpd = HazardPointDetail.objects.filter(hazard_point=hp, wave_height__gte=wh-whd, wave_height__lte=wh+whd).order_by('return_period')
            length = len(hpd)
            if(length == 0):
                # Should handle for this and pick a return period that is 'close'
                return HttpResponse('No return periods in range', status=400)
            return HttpResponse(serializers.serialize("json", [hpd[int(length/2)]], fields=('return_period')))
        except:
            #traceback.print_exc(file=sys.stdout)
            return HttpResponse('Unexpected Error', status=500)

def return_periods(request):
    return HttpResponse(simplejson.dumps(RETURN_PERIOD_CHOICES))

def hazard_points(request):
    if "rp" in request.GET:
        # Not sure how to do this with the Django ORM
        '''
        select tsudat_hazardpoint.id, 
            tsudat_hazardpoint.tsudat_id, 
            tsudat_hazardpointdetail.wave_height, 
            tsudat_hazardpointdetail.color, 
            tsudat_hazardpoint.geom 
        from tsudat_hazardpoint 
        inner join tsudat_hazardpointdetail on tsudat_hazardpoint.id = tsudat_hazardpointdetail.hazard_point_id 
        where tsudat_hazardpointdetail.return_period = 100;
        '''
        return HttpResponse("not yet", status=501)
    else:
        hp = HazardPoint.objects.all()
        djf = Django.Django(geodjango="geom", properties=['tsudat_id'])
        return HttpResponse(geoj.encode(djf.decode(hp)))

def source_zones(request):
    # Currently the geom fields are not populated
    return HttpResponse(serializers.serialize("json", SourceZone.objects.all(), fields=('id', 'tsudat_id','name')))

def source_zone(request):
    if "sf" in request.GET:
        try:
            sf = SubFault.objects.get(tsudat_id=int(request.GET.get('sf')))
            return HttpResponse(serializers.serialize("json", [sf.source_zone]))
        except:
            # ToDo catch individual errors
            return HttpResponse('Error', status=400)
    else:
        return HttpResponse('Sub Fault must be specified', status=400)


def sub_faults(request):
    if "sz" in request.GET:
        try:
            sz = SourceZone.objects.get(id=int(request.GET.get('sz')))
            sf = SubFault.objects.filter(source_zone = sz)
        except:
            return HttpResponse("invalid source zone", status=404)
    elif "event" in request.GET:
        try:
            event = Event.objects.get(tsudat_id=int(request.GET.get("event")))
            return HttpResponse(serializers.serialize("json", event.sub_faults.all()))
        except:
            # ToDo catch individual errors
            return HttpResponse('Error', status=400)
    else:
        sf = SubFault.objects.all()
        # How do we serialize the source_zone properly   
    djf = Django.Django(geodjango="geom", properties=['tsudat_id', 'dip', 'strike'])
    return HttpResponse(geoj.encode(djf.decode(sf)))

def events(request):
    if not "wh" in request.GET: 
        return HttpResponse('Wave Height must be specified', status=400) 
    elif not "whd" in request.GET: 
        return HttpResponse('Wave Height Delta must be specified', status=400) 
    elif not "hp" in request.GET: 
        return HttpResponse('Hazard Point must be specified', status=400)
    elif not "sz" in request.GET: 
        return HttpResponse('Source Zone must be specified', status=400)
    else:
        try:
            hp = HazardPoint.objects.get(tsudat_id=int(request.GET.get('hp')))
        except:
            return HttpResponse('Invalid Hazard Point', status=400) 
        try:
            sz = SourceZone.objects.get(tsudat_id=int(request.GET.get('sz')))
        except:
            return HttpResponse('Invalid Hazard Point', status=400) 
        try:
            wh = float(request.GET.get('wh'))
            whd = float(request.GET.get('whd'))
        except:
            return HttpResponse('Invalid Wave Height or Delta', status=400) 
        try:
            ewh = EventWaveHeight.objects.filter(event__source_zone=sz, hazard_point=hp, wave_height__gte=wh-whd, wave_height__lte=wh+whd)
            return HttpResponse(serializers.serialize("json", ewh))
        except:
            #traceback.print_exc(file=sys.stdout) 
            return HttpResponse('Unexpected Error', status=400) 

def wave_height(request):
    if not "rp" in request.GET: 
        return HttpResponse('Return Period must be specified', status=400) 
    elif not "hp" in request.GET: 
        return HttpResponse('Hazard Point must be specified', status=400) 
    else:
        try:
            hp = HazardPoint.objects.get(tsudat_id=int(request.GET.get('hp')))
        except:
            return HttpResponse('Invalid Hazard Point', status=400) 
        try:
            if(int(request.GET.get('rp')) not in RETURN_PERIODS):
                return HttpResponse('Invalid Return Period', status=400) 
            else:
                rp = int(request.GET.get('rp'))
        except:
            return HttpResponse('Invalid Return Period', status=400) 
        try:
            hpd = HazardPointDetail.objects.get(hazard_point=hp, return_period=rp)
            return HttpResponse(serializers.serialize("json", [hpd]))
        except:
            #traceback.print_exc(file=sys.stdout) 
            return HttpResponse('Unexpected Error', status=500)

@csrf_exempt
def project(request, id=None):
    if id == None and request.method == "POST":
        data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
        p = Project()
        p.from_json(data)
        djf = Django.Django(geodjango="geom", properties=['name'])
        return HttpResponse(geoj.encode(djf.decode([p])))
    elif id != None and id != "all":
        p = Project.objects.get(pk=id)
        djf = Django.Django(geodjango="geom", properties=['name'])
        return HttpResponse(geoj.encode(djf.decode([p])))
    else:
        projects = Project.objects.all()
        djf = Django.Django(geodjango="geom", properties=['name'])
        return HttpResponse(geoj.encode(djf.decode(projects)))

@csrf_exempt
def internal_polygon(request, id=None):
    #TODO: GET polygons for project_id and/or type
    if id == None and request.method == "POST":
        try:
            data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            ip = InternalPolygon()
            ip.from_json(data)
            djf = Django.Django(geodjango="geom", properties=['project_id','type', 'value'])
            return HttpResponse(geoj.encode(djf.decode([ip])))
            return HttpResponse("")
        except:
            return HttpResponse('Unexpected Error', status=500)
            #traceback.print_exc(file=sys.stdout) 
	    
    elif id != None and id != "all":
        ip = InternalPolygon.objects.get(pk=id)
        djf = Django.Django(geodjango="geom", properties=['project_id','type', 'value'])
        return HttpResponse(geoj.encode(djf.decode([ip])))
    else:
        ips = InternalPolygon.objects.all()
        djf = Django.Django(geodjango="geom", properties=['project_id','type', 'value'])
        return HttpResponse(geoj.encode(djf.decode(ips)))

@csrf_exempt
def gauge_point(request, id=None):
    #TODO: GET gauge points for project_id and/or type
    if id == None and request.method == "POST":
        try:
            data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            gp = GaugePoint.encode(djf.decode(data))
            gp.from_json(data)
            djf = Django.Django(geodjango="geom", properties=['project_id','name'])
            return HttpResponse(geoj.encode(djf.decode([gp])))
        except:
	    # Todo catch specific errors and return proper http response code and message
            return HttpResponse('Unexpected Error', status=500)
            #traceback.print_exc(file=sys.stdout) 
    elif id != None and id != "all":
        gp = GaugePoint.objects.get(pk=id)
        djf = Django.Django(geodjango="geom", properties=['project_id','name'])
        return HttpResponse(geoj.encode(djf.decode([gp])))
    else:
        gps = GaugePoint.objects.all()
        djf = Django.Django(geodjango="geom", properties=['project_id','name'])
        return HttpResponse(geoj.encode(djf.decode(gps)))

@csrf_exempt
def scenario(request, id=None):
    #TODO: GET scenarios for a project (other params?) 
    if id == None and request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data) 
            scenario = Scenario()
            scenario.from_json(data)
            return HttpResponse(serializers.serialize("json", [scenario]))
        except:
	    # Todo catch specific errors and return proper http response code and message
            return HttpResponse('Unexpected Error', status=500)
            #traceback.print_exc(file=sys.stdout)
    elif id != None and id != "all":
        scenario = Scenario.objects.get(pk=id)
        return HttpResponse(serializers.serialize("json", [scenario]))
    else:
        scenarios = Scenario.objects.all()
        return HttpResponse(serializers.serialize("json", scenarios))

@csrf_exempt
def data_set(request, id=None):
    if("project_id" in request.GET):
    	project = Project.objects.get(id=int(request.GET.get('project_id')))
        project_geom = project.geom
	ds = DataSet.objects.filter(geom__intersects=project_geom)
	return HttpResponse(serializers.serialize("json", ds))
    elif id != None and id != "all":
        data_set = DataSet.objects.get(pk=id)
        return HttpResponse(serializers.serialize("json", [data_set]))
    else:
	#Update from GeoNode Database
	coverage_layers = Layer.objects.using('geonode').filter(storeType="coverageStore")
	for layer in coverage_layers:
		try:
			ds = DataSet.objects.get(geonode_layer_uuid=layer.uuid)
			#update existing?
		except ObjectDoesNotExist:
			ds = DataSet()
			ds.geonode_layer_uuid = layer.uuid
			ds.data_type = 'U'
			ds.resolution = 0
			geom_wkt = layer.geographic_bounding_box
			if(geom_wkt.find('EPSG') != -1):
				epsg = (geom_wkt.split(';')[0].split('=')[1])
                		geom = GEOSGeometry(geom_wkt.split(';')[1])
				srs = SpatialReference(epsg)
                		geom.set_srid(srs.srid)
                		geom.transform(4326)
				ds.geom = geom
			else:
				ds.geom = GEOSGeometry(geom_wkt)
			ds.save()
        data_sets = DataSet.objects.all()
        return HttpResponse(serializers.serialize("json", data_sets))

@csrf_exempt
def project_data_set(request, id=None):
    if id == None and request.method == "POST":
        try:
            data = simplejson.loads(request.raw_post_data) 
            project_data_set = ProjectDataSet()
            project_data_set.from_json(data)
            return HttpResponse(serializers.serialize("json", [project_data_set]))
        except:
	    # Todo catch specific errors and return proper http response code and message
            return HttpResponse('Unexpected Error ' + str(sys.exc_info()[0]), status=500)
            #traceback.print_exc(file=sys.stdout)
    elif id != None and id != "all":
        project_data_set = ProjectDataSet.objects.get(pk=id)
        return HttpResponse(serializers.serialize("json", [project_data_set]))
    else:
        project_data_sets = ProjectDataSet.objects.all()
        return HttpResponse(serializers.serialize("json", project_data_sets))

def layer(request, uuid=None):
	if(uuid != None):
		layer = Layer.objects.using('geonode').get(uuid=uuid)
		return HttpResponse(serializers.serialize("json", [layer]))
	if("project_id" in request.GET):
		coverage_layers = Layer.objects.using('geonode').filter(storeType="coverageStore")
		project = Project.objects.get(id=int(request.GET.get('project_id')))
		project_geom = project.geom
		project_area_layers = []
		for layer in coverage_layers:
			geom_wkt = layer.geographic_bounding_box
			if(geom_wkt.find('EPSG') != -1):
				epsg = (geom_wkt.split(';')[0].split('=')[1])
                		geom = GEOSGeometry(geom_wkt.split(';')[1])
				srs = SpatialReference(epsg)
                		geom.set_srid(srs.srid)
                		geom.transform(4326)
			else:
				geom = GEOSGeometry(geom_wkt)
			if(geom.intersects(project_geom)):
				project_area_layers.append(layer)
		return HttpResponse(serializers.serialize("json", project_area_layers))
	else:
		coverage_layers = Layer.objects.using('geonode').filter(storeType="coverageStore")
		return HttpResponse(serializers.serialize("json", coverage_layers))

def run_scenario(request, scenario_id):
    try:
        #logger.debug("Calling run_tsudat_simulation asynchronously")
        run_tsudat_simulation.delay(request.user, scenario_id)
        data = {'status': 'success', 'msg': 'Scenario queued for processing'}
        return HttpResponse(simplejson.dumps(data), mimetype='application/json')
    except:
        data = {'status': 'failure', 'msg': 'Failed queuing Scenario for processing', 'error': str(sys.exc_info()[0])}
        return HttpResponse(simplejson.dumps(data),mimetype='application/json')
