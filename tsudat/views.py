import simplejson

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.core import serializers

from vectorformats.Formats import Django, GeoJSON

from tsudat.models import *

geoj = GeoJSON.GeoJSON()

def index(request):
    return render_to_response('tsudat/index.html')

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
        return HttpResponse("not yet", status_code=501)
    else:
        hp = HazardPoint.objects.all()
        djf = Django.Django(geodjango="geom", properties=['tsudat_id'])
        return HttpResponse(geoj.encode(djf.decode(hp)))

def source_zones(request):
    # Currently the geom fields are not populated
    return HttpResponse(serializers.serialize("json", SourceZone.objects.all(), fields=('id', 'tsudat_id','name')))

def sub_faults(request):
    if "sz" in request.GET:
        try:
            sz = SourceZone.objects.get(id=int(request.GET.get('sz')))
            sf = SubFault.objects.filter(source_zone = sz)
        except:
            return HttpResponse("invalid source zone", status_code=404)
    else:
        sf = SubFault.objects.all()
        # How do we serialize the source_zone properly   
    djf = Django.Django(geodjango="geom", properties=['tsudat_id', 'dip', 'strike'])
    return HttpResponse(geoj.encode(djf.decode(sf)))

def events(request):
    # Will *never* get all events like this.
    return HttpResponse(serializers.serialize("json", Event.objects.all()))
