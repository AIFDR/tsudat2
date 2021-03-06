import os, sys
import traceback
import simplejson as json
import geojson
import datetime

from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.http import HttpResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt, csrf_response_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.gis.geos import *
from django.conf import settings
from django.template import RequestContext
from django.db.models import Avg, Max, Min, Count

from vectorformats.Formats import Django, GeoJSON

from geonode.maps.models import *

from tsudat.models import *
from tsudat.tasks import run_tsudat_simulation, download_tsunami_waveform

import logging
logger = logging.getLogger("tsudat2.tsudat.views")

geoj = GeoJSON.GeoJSON()

def index(request):
    return redirect('/tsudat2-client/')

def about(request):
    return render_to_response("about.html")

def disclaimer(request):
    return render_to_response("disclaimer.html", RequestContext(request, {
        "GEOSERVER_BASE_URL": settings.GEOSERVER_BASE_URL,
        "GEONETWORK_BASE_URL": settings.GEONETWORK_BASE_URL,
        "STATIC_URL": settings.SITEURL
    }))


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
            wh = float(request.GET.get('wh'))
            whd = float(request.GET.get('whd'))
            hpd = HazardPointDetail.objects.filter(hazard_point=hp, wave_height__gte=wh-whd, wave_height__lte=wh+whd).order_by('return_period')
            length = len(hpd)
            if(length == 0):
                # Should handle for this and pick a return period that is 'close'
                return HttpResponse('No return periods in range', status=400)
            return HttpResponse(serializers.serialize("json", [hpd[int(length/2)]], fields=('return_period')))
        except ObjectDoesNotExist:
            return HttpResponse('Invalid Hazard Point', status=404) 
        except ValueError:
            return HttpResponse('Invalid Wave Height or Wave Height Delta', status=400)
        except:
            return HttpResponse(('Unexpected Error %s' % ( str(sys.exc_info()))), status=500)

def return_periods(request):
    return HttpResponse(json.dumps(RETURN_PERIOD_CHOICES), mimetype='application/json')

def hazard_point_style(request):
    if "rp" in request.GET:
        rp = int(request.GET.get('rp'))
        results = HazardPointDetail.objects.filter(return_period=rp).aggregate(Min('wave_height'),  Max('wave_height'))
        min = results['wave_height__min']
        max = results['wave_height__max']
        if min is None and max is None:
            min = 0
            max = 0
        interval = ((max - min) / 5)
        return render_to_response("hp_rp.xml", RequestContext(request, {
            "max": max,
            "min": min,
            "cls1s": min,
            "cls1e": min+interval,
            "cls2s": min+interval,
            "cls2e": min+interval*2,
            "cls3s": min+interval*2,
            "cls3e": min+interval*3,
            "cls4s": min+interval*3,
            "cls4e": min+interval*4,
            "cls5s": min+interval*4,
            "cls5e": max,
        }), mimetype="application/sld")
    else:
        pass

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
        try:
            hp = HazardPoint.objects.all()
            djf = Django.Django(geodjango="geom", properties=['tsudat_id'])
            return HttpResponse(geoj.encode(djf.decode(hp)))
        except:
            return HttpResponse('Unexpected Error', status=500)

def source_zones(request):
    # Currently the geom fields are not populated
    return HttpResponse(serializers.serialize("json", SourceZone.objects.all(), fields=('id', 'tsudat_id','name')))

def source_zone(request):
    if "sf" in request.GET:
        try:
            sf = SubFault.objects.get(tsudat_id=int(request.GET.get('sf')))
            return HttpResponse(serializers.serialize("json", [sf.source_zone]))
        except ObjectDoesNotExist:
            return HttpResponse('Invalid Hazard Point', status=400) 
        except:
            return HttpResponse('Unexpected Error', status=500)
    else:
        return HttpResponse('Sub Fault must be specified', status=400)

def sub_faults(request):
    if "event" in request.GET:
        try:
            event = Event.objects.get(tsudat_id=int(request.GET.get("event")))
            return HttpResponse(serializers.serialize("json", event.sub_faults.all()))
        except ObjectDoesNotExist:
            return HttpResponse('Invalid Event', status=404)
        except:
            return HttpResponse('Unexpected Error', status=500)
    elif "sz" in request.GET:
        try:
            sz = SourceZone.objects.get(id=int(request.GET.get('sz')))
            sf = SubFault.objects.filter(source_zone = sz)
        except ObjectDoesNotExist:
            return HttpResponse("invalid source zone", status=404)
        except:
            return HttpResponse('Unexpected Error', status=500)
    else:
        sf = SubFault.objects.all()
        # How do we serialize the source_zone properly
    if(sf != None):
        djf = Django.Django(geodjango="geom", properties=['tsudat_id', 'dip', 'strike'])
        return HttpResponse(geoj.encode(djf.decode(sf)))
    else:
        return HttpResponse("invalid source zone", status=404)

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
            try:
                hp = HazardPoint.objects.get(tsudat_id=int(request.GET.get('hp')))
            except ObjectDoesNotExist:
                return HttpResponse('Invalid Hazard Point', status=400) 
            try:
                sz = SourceZone.objects.get(tsudat_id=int(request.GET.get('sz')))
            except ObjectDoesNotExist:
                return HttpResponse('Invalid Source Zone', status=400) 
            try:
                wh = float(request.GET.get('wh'))
                whd = float(request.GET.get('whd'))
            except ValueError:
                return HttpResponse('Invalid Wave Height or Delta', status=400) 
            ewh = EventWaveHeight.objects.filter(event__source_zone=sz, hazard_point=hp, wave_height__gte=wh-whd, wave_height__lte=wh+whd)
            return HttpResponse(serializers.serialize('json', ewh, relations=('event',)))
        except:
            return HttpResponse('Unexpected Error', status=400) 

def wave_height(request):
    if not "rp" in request.GET: 
        return HttpResponse('Return Period must be specified', status=400) 
    elif not "hp" in request.GET: 
        return HttpResponse('Hazard Point must be specified', status=400) 
    else:
        try:
            hp = HazardPoint.objects.get(tsudat_id=int(request.GET.get('hp')))
        except ObjectDoesNotExist:
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
            return HttpResponse('Unexpected Error %s' %  str(sys.exc_info()), status=500)

@csrf_exempt
def polygon_from_csv(request):
    if request.method == "POST":
        try:
            csv_file = request.FILES['csv_file']
            count = 0
            coords = []
            row0 = []
            for row in csv_file.readlines():
                parts = row.strip().split(',')
                x = float(parts[0])
                y = float(parts[1])
                coords.append((x,y))
                if count == 0:
                    row0 = (x,y)
                count += 1
            coords.append(row0)
            geom = Polygon(coords)
            if "srs" in request.POST:
                srs = request.POST.get('srs')
                srs = SpatialReference(srs)
                geom.set_srid(srs.srid)
                geom.transform(4326)
            return HttpResponse(geom.json, mimetype='text/html')
        except:
            data = {'status': 'failure', 'msg': 'Conversion to Polygon Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='text/html')
    else:
        data = {'status': 'failure', 'msg': 'Conversion to Polygon Failed', 'reason': 'Invalid Request (not POST)'}
        return HttpResponse(json.dumps(data), status=400, mimetype='text/html')

@csrf_exempt
def project(request, id=None):
    if id == None and request.method == "POST":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to save new projects',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            except:
                data = {'status': 'failure', 'msg': 'Project Creation Failed', 'reason': 'Invalid GeoJSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            p = Project()
            p.user = request.user
            p, reason = p.from_json(data)
            if p is None:
                data = {'status': 'failure', 'msg': 'Project Creation Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Project Creation Successful', 'id': p.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Project Creation Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    elif id != None and request.method == "PUT":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to save projects',
                mimetype="text/plain",
                status=401
            )
        try:
            data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            p = Project.objects.get(pk=id)
            p, reason = p.from_json(data)
            if(p is None):
                data = {'status': 'failure', 'msg': 'Project Update Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Project Update Successful', 'id': p.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Project Update Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    elif id != None and request.method == "DELETE":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to delete projects',
                mimetype="text/plain",
                status=401
            )
        try:
            p = Project.objects.get(pk=id)
            p.delete()
            data = {'status': 'success', 'msg': 'project deleted'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Project Delete Failed', 'reason': 'Invalid Project'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Project Delete Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    elif id != None and id != "all" and request.method == "GET":
        try:
            p = Project.objects.get(pk=id)
            djf = Django.Django(geodjango="geom", properties=['name', 'max_area'])
            return HttpResponse(geoj.encode(djf.decode([p])))
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Unable to Retrieve Project', 'reason': 'Invalid Project'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Unable to Retrieve Project', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    else:
        try:
            projects = Project.objects.all()
            djf = Django.Django(geodjango="geom", properties=['name', 'max_area'])
            return HttpResponse(geoj.encode(djf.decode(projects)))
        except:
            data = {'status': 'failure', 'msg': 'Unable to Retrieve Projects', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')

def internal_polygon_types(request):
    return HttpResponse(json.dumps(IP_TYPE_CHOICES))

@csrf_exempt
def internal_polygon(request, id=None):
    if id == None and request.method == "POST":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            except:
                data = {'status': 'failure', 'msg': 'Internal Polygon Creation Failed', 'reason': 'Invalid GeoJSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            ip = InternalPolygon()
            ip, reason = ip.from_json(data)
            if ip is None:
                data = {'status': 'failure', 'msg': 'Internal Polygon Creation Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Internal Polygon Creation Successful', 'id': ip.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Internal Polygon Creation Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
    elif id != None and request.method == "PUT":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            except:
                data = {'status': 'failure', 'msg': 'Internal Polygon Creation Failed', 'reason': 'Invalid GeoJSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            try:
                ip = InternalPolygon.objects.get(pk=id)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Internal Polygon Creation Failed', 'reason': 'Invalid Internal Polygon'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            ip, reason = ip.from_json(data)
            if ip is None:
                data = {'status': 'failure', 'msg': 'Internal Polygon Update Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Internal Polygon Update Successful', 'id': ip.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Internal Polygon Update Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and request.method == "DELETE":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                ip = InternalPolygon.objects.get(pk=id)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Internal Polygon Delete Failed', 'reason': 'Invalid Internal Polygon'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            ip.delete()
            data = {'status': 'success', 'msg': 'internal polygon deleted'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Internal Polygon Delete Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and id != "all" and request.method == "GET":
        try:
            try:
                ip = InternalPolygon.objects.get(pk=id)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Internal Polygon Delete Failed', 'reason': 'Invalid Internal Polygon'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            djf = Django.Django(geodjango="geom", properties=['project_id','type', 'value'])
            return HttpResponse(geoj.encode(djf.decode([ip])))
        except:
            data = {'status': 'failure', 'msg': 'Unable to retrieve Internal Polygon', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    else:
        if "project" in request.GET:
            try:
                project = Project.objects.get(pk=int(request.GET.get('project')))
                ips = InternalPolygon.objects.filter(project=project)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Unable to retrieve Internal Polygons', 'reason': 'Unexpected Error'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        else:
            try:
                ips = InternalPolygon.objects.all()
            except:
                data = {'status': 'failure', 'msg': 'Unable to retrieve Internal Polygons', 'reason': 'Unexpected Error'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        djf = Django.Django(geodjango="geom", properties=['project_id','type', 'value'])
        return HttpResponse(geoj.encode(djf.decode(ips)))

@csrf_exempt
def gauge_point(request, id=None):
    if id == None and request.method == "POST":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            except:
                data = {'status': 'failure', 'msg': 'Gauge Point Creation Failed', 'reason': 'Invalid GeoJSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            gp = GaugePoint()
            gp, reason = gp.from_json(data)
            if gp is None:
                data = {'status': 'failure', 'msg': 'Gauge Point Creation Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'failure', 'msg': 'Gauge Point Creation Successful', 'id': gp.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Gauge Point Creation Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
    elif id != None and request.method == "PUT":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = geojson.loads(request.raw_post_data, object_hook=geojson.GeoJSON.to_instance)
            except:
                data = {'status': 'failure', 'msg': 'Gauge Point Creation Failed', 'reason': 'Invalid GeoJSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            try:
                gp = GaugePoint.objects.get(pk=id)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Gauge Point Update Failed', 'reason': 'Invalid Gauge Point'}
                return HttpResponse(json.dumps(data), mimetype='application/json')
            gp, reason = gp.from_json(data)
            if gp is None:
                data = {'status': 'failure', 'msg': 'Gauge Point Update Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'failure', 'msg': 'Gauge Point Update Successful', 'id': gp.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Gauge Point Update Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and request.method == "DELETE":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            gp = GaugePoint.objects.get(pk=id)
            gp.delete()
            data = {'status': 'success', 'msg': 'gauge point deleted'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Gauge Point Delete Failed', 'reason': 'Invalid Gauge Point'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Gauge Point Delete Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and id != "all":
        try:
            gp = GaugePoint.objects.get(pk=id)
            djf = Django.Django(geodjango="geom", properties=['project_id','name'])
            return HttpResponse(geoj.encode(djf.decode([gp])))
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Unable to retrieve Gauge Point', 'reason': 'Invalid Gauge Point'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Unable to retrieve Gauge Point', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    else:
        if "project" in request.GET:
            try:
                project = Project.objects.get(pk=int(request.GET.get('project')))
                gps = GaugePoint.objects.filter(project=project)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Unable to retrieve Gauge Points', 'reason': 'Unexpected Error'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        else:
            try:
                gps = GaugePoint.objects.all()
            except:
                data = {'status': 'failure', 'msg': 'Unable to retrieve Gauge Points', 'reason': 'Unexpected Error'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        djf = Django.Django(geodjango="geom", properties=['project_id','name'])
        return HttpResponse(geoj.encode(djf.decode(gps)))

@csrf_exempt
def scenario(request, id=None):
    if id == None and request.method == "POST":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            data = json.loads(request.raw_post_data) 
            s = Scenario()
            s,reason = s.from_json(data)
            if s is None:
                data = {'status': 'failure', 'msg': 'Scenario Creation Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                s.anuga_status = "INIT"
                s.tsudat_start_timestamp = datetime.now() 
                s.save()
                data = {'status': 'success', 'msg': 'Scenario Creation Successful', 'id': s.pk}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Scenario Creation Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    elif id != None and request.method == "PUT":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            data = json.loads(request.raw_post_data) 
            s = Scenario(pk=id)
            s, reason = s.from_json(data)
            if s is None:
                data = {'status': 'failure', 'msg': 'Scenario Update Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Scenario Update Successful', 'id': s.pk}
                s.anuga_status = "UPDT"
                s.save()
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Scenario Update Failed', 'reason': 'Invalid Scenario'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Scenario Update Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    elif id != None and request.method == "DELETE":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            scenario = Scenario(pk=id)
            scenario.delete()
            data = {'status': 'success', 'msg': 'scenario deleted'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Scenario Delete Failed', 'reason': 'Invalid Scenario'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Scenario Delete Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    elif id != None and id != "all":
        try:
            scenario = Scenario.objects.get(pk=id)
            return HttpResponse(serializers.serialize("json", [scenario]))
        except:
            data = {'status': 'failure', 'msg': 'Scenario Get Failed', 'reason': 'Invalid Scenario'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')
    else:
        if "project" in request.GET:
            try:
                project = Project.objects.get(pk=int(request.GET.get('project')))
                scenarios = Scenario.objects.filter(project=project)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Unable to retrieve Scenarios', 'reason': 'Unexpected Error'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        else:
            try:
                scenarios = Scenario.objects.all()
            except:
                data = {'status': 'failure', 'msg': 'Unable to retrieve Scenarios', 'reason': 'Unexpected Error'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        try:
            return HttpResponse(serializers.serialize("json", scenarios))
        except:
            data = {'status': 'failure', 'msg': 'Unable to retrieve Scenarios', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=500, mimetype='application/json')

def scenario_list(request):
    if(request.user.is_superuser):
        scenarios = Scenario.objects.all().order_by('-pk')
    else: 
        scenarios = Scenario.objects.filter(project__user = request.user).order_by('-pk')
    return render_to_response("scenario_list.html", RequestContext(request, {
        "scenarios": scenarios,
    }))

def scenario_info(request, id=None):
    s = get_object_or_404(Scenario, pk=id)
    apl = s.anuga_payload
    gauges = []
    gauges_csv = []
    logs = []
    if(apl):
        payload = apl.replace('u\'', '\'')
        payload = payload.replace('\'', '\"')
        pl = json.loads(payload)
        for gauge in pl['timeseries_plot']:
            val = gauge.replace('/data', '/tsudat-media')
            gauges.append({'png': val, 'csv': val.replace('.png', '.csv')})
        for gauge_csv in pl['hpgauges']:
            val = gauge_csv.replace('/data', '/tsudat-media')
            (head, tail) = os.path.split(val)
            gauges_csv.append({tail: val})
        for log in pl['log']:
            val = log.replace('/data', '/tsudat-media')
            (head, tail) = os.path.split(val)
            logs.append({tail: val})
    return render_to_response("scenario_info.html", RequestContext(request, {
        "scenario": s, 
        "gauges": gauges,
        "gauges_csv": gauges_csv,
        "logs": logs,
    }))

def refresh_ds_from_geonode():
    #Update from GeoNode Database
    coverage_layers = Layer.objects.filter(storeType="coverageStore")
    for layer in coverage_layers:
        try:
            ds = DataSet.objects.get(typename=layer.typename)
            #update existing?
        except ObjectDoesNotExist:
            ds = DataSet()
            ds.geonode_layer_uuid = layer.uuid
            ds.typename = layer.typename
            ds.data_type = 'U'
            ds.resolution = 0
            geom_wkt = layer.geographic_bounding_box
            if(len(geom_wkt) < 1):
                pass # Not sure what to do here
            else:
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

@csrf_exempt
def data_set(request, id=None):
    if("project_id" in request.GET):
        try:
            refresh_ds_from_geonode()
            project = Project.objects.get(id=int(request.GET.get('project_id')))
            project_geom = project.geom
            ds = DataSet.objects.filter(geom__intersects=project_geom)
            return HttpResponse(serializers.serialize("json", ds))
        except:
            return HttpResponse('Unexpected Error', status=500)
    elif id != None and id != "all":
        try:
            refresh_ds_from_geonode()
            data_set = DataSet.objects.get(pk=id)
            return HttpResponse(serializers.serialize("json", [data_set]))
        except ObjectDoesNotExist:
            return HttpResponse('Invalid DataSet', status=404)
        except:
            return HttpResponse('Unexpected Error', status=500)
    else:
        refresh_ds_from_geonode()
        data_sets = DataSet.objects.all()
        return HttpResponse(serializers.serialize("json", data_sets))

@csrf_exempt
def project_data_set(request, id=None):
    if id == None and request.method == "POST":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = json.loads(request.raw_post_data) 
            except:
                data = {'status': 'failure', 'msg': 'Project Dataset Creation Failed', 'reason': 'Invalid JSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            pds = ProjectDataSet()
            pds, reason = pds.from_json(data)
            if pds is None:
                data = {'status': 'failure', 'msg': 'Project Dataset Creation Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Project Dataset Creation Successful', 'id': pds.id}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Project Dataset Creation Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and request.method == "PUT":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                data = json.loads(request.raw_post_data) 
            except:
                data = {'status': 'failure', 'msg': 'Project Dataset Update Failed', 'reason': 'Invalid JSON'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            try:
                pds = ProjectDataSet(pk=id)
            except ObjectDoesNotExist:
                data = {'status': 'failure', 'msg': 'Project Dataset Update Failed', 'reason': 'Invalid Project Dataset'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            pds, reason = pds.from_json(data)
            if pds is None:
                data = {'status': 'failure', 'msg': 'Project Dataset Update Failed', 'reason': reason}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            else:
                data = {'status': 'success', 'msg': 'Project Dataset Update Successful', 'id': pds.id}
                return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Project Dataset Update Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and request.method == "DELETE":
        if not request.user.is_authenticated():
            return HttpResponse(
                'You must be logged in to perform this action',
                mimetype="text/plain",
                status=401
            )
        try:
            try:
                project_data_set = ProjectDataSet(pk=id)
            except:
                data = {'status': 'failure', 'msg': 'Project Dataset Delete Failed', 'reason': 'Invalid Project Dataset'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
            project_data_set.delete()
            data = {'status': 'success', 'msg': 'project deleted'}
            return HttpResponse(json.dumps(data), mimetype='application/json')
        except:
            data = {'status': 'failure', 'msg': 'Project Dataset Delete Failed', 'reason': 'Unexpected Error'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    elif id != None and id != "all":
        try:
            project_data_set = ProjectDataSet.objects.get(pk=id)
            return HttpResponse(serializers.serialize("json", [project_data_set]))
        except ObjectDoesNotExist:
            data = {'status': 'failure', 'msg': 'Project Dataset Delete Failed', 'reason': 'Invalid Project Dataset'}
            return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
    else:
        if "project_id" in request.GET:
            try:
                project = Project.objects.get(pk=int(request.GET.get("project_id")))
                project_data_sets = ProjectDataSet.objects.filter(project=project)
            except:
                data = {'status': 'failure', 'msg': 'ProjectDataSet GET Failed', 'reason': 'Invalid Project'}
                return HttpResponse(json.dumps(data), status=400, mimetype='application/json')
        else:
            project_data_sets = ProjectDataSet.objects.all()
        return HttpResponse(serializers.serialize("json", project_data_sets))

def layer(request, uuid=None):
	if(uuid != None):
		layer = Layer.objects.get(uuid=uuid)
		return HttpResponse(serializers.serialize("json", [layer]))
	if("project_id" in request.GET):
		coverage_layers = Layer.objects.filter(storeType="coverageStore")
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
		coverage_layers = Layer.objects.filter(storeType="coverageStore")
		return HttpResponse(serializers.serialize("json", coverage_layers))

@csrf_exempt
def download_waveform(request):
    try:
        download_tsunami_waveform.delay(request.user, [request.GET.get('project_id'), request.GET.get('event_id')])    
        data = {'status': 'success', 'msg': 'Scenario Download queued for processing'}
        return HttpResponse(json.dumps(data), mimetype='application/json')
    except:
        data = {'status': 'failure', 'msg': 'Failed queuing Scenario Download for processing', 'error': str(sys.exc_info()[0])}
        return HttpResponse(json.dumps(data),mimetype='application/json')

@csrf_exempt
def download_scenario(request, scenario_id):
    try:
        
        download_scenario.delay(request.user, scenario_id)    
        data = {'status': 'success', 'msg': 'Scenario Download queued for processing'}
        return HttpResponse(json.dumps(data), mimetype='application/json')
    except:
        data = {'status': 'failure', 'msg': 'Failed queuing Scenario Download for processing', 'error': str(sys.exc_info()[0])}
        return HttpResponse(json.dumps(data),mimetype='application/json')

@csrf_exempt
def run_scenario(request, scenario_id):
    try:
        #logger.debug("Calling run_tsudat_simulation asynchronously")
        run_tsudat_simulation.delay(request.user, scenario_id)
        data = {'status': 'success', 'msg': 'Scenario queued for processing'}
        return HttpResponse(json.dumps(data), mimetype='application/json')
    except:
        data = {'status': 'failure', 'msg': 'Failed queuing Scenario for processing', 'error': str(sys.exc_info()[0])}
        return HttpResponse(json.dumps(data),mimetype='application/json')
