import sys, traceback
import simplejson
import geojson

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt, csrf_response_exempt

from vectorformats.Formats import Django, GeoJSON

from tsudat.models import *

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
            gp = GaugePoint()
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
