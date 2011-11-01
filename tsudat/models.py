import sys, traceback
import geojson
from django.contrib.gis.geos import GEOSGeometry, LinearRing, LineString
from django.contrib.gis.gdal import SpatialReference
from django.contrib.gis.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User

from geonode.maps.models import Layer, Map, MapLayer

import logging
logger = logging.getLogger("tsudat2.tsudat.models")

RETURN_PERIOD_CHOICES = (
    (10, '10 years'),
    (25, '25 years'),
    (50, '50 years'),
    (75, '75 years'),
    (100, '100 years'),
    (150, '150 years'),
    (200, '200 years'),
    (250, '250 years'),
    (500, '500 years'),
    (750, '750 years'),
    (1000, '1000 years'),
    (1500, '1500 years'),
    (2000, '2000 years'),
    (3000, '3000 years'),
    (4000, '4000 years'),
    (5000, '5000 years'),
    (7500, '7500 years'),
    (10000, '10000 years'),
    (25000, '25000 years'),
    (50000, '50000 years'),
    (75000, '75000 years'),
    (100000, '100000 years'),
)

RETURN_PERIODS = [ rp for (rp, _) in RETURN_PERIOD_CHOICES]

IP_TYPE_CHOICES = (
    (1, 'Mesh Resolution'),
    (2, 'Mesh Friction'),
    (3, 'Area of Interest'),
)

DATASET_TYPE_CHOICES = (
    ('U', 'UNKNOWN'),
    ('G', 'GEBCO'),
    ('L', 'LIDAR'),
    ('S', 'SRTM'),
)

MODEL_SETUP_CHOICES = (
    ('T', 'Trial'),
    ('B', 'Basic'),
    ('F', 'Final'),
)


#Required to do a ManyToMany in Scenario
class ScenarioOutputLayer(models.Model):
    name = models.CharField(max_length=10)
    description = models.CharField(max_length=100)
    def __unicode__(self):
        return self.name

class HazardPoint(models.Model):
    tsudat_id = models.PositiveIntegerField()
    geom = models.PointField()
    
    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.tsudat_id)

class HazardPointDetail(models.Model):
    hazard_point = models.ForeignKey(HazardPoint)
    return_period = models.IntegerField(choices=RETURN_PERIOD_CHOICES)
    wave_height = models.FloatField(null=True, blank=True) # Min 0, Max 10
    color = models.CharField(max_length=8, null=True, blank=True)

    def __unicode__(self):
        return str(self.pk)

class SourceZone(models.Model):
    tsudat_id = models.PositiveIntegerField()
    name = models.CharField(max_length=20)
    geom = models.LineStringField(null=True, blank=True)
    
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

class SubFault(models.Model):
    tsudat_id = models.PositiveIntegerField()
    source_zone = models.ForeignKey(SourceZone)
    geom = models.PointField()
    dip = models.FloatField( null=True, blank=True)
    strike = models.PositiveIntegerField(null=True, blank=True) # 0-360
    
    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.tsudat_id)

class SubFaultDetail(models.Model):
    hazard_point = models.ForeignKey(HazardPoint)
    sub_fault = models.ForeignKey(SubFault)
    return_period = models.IntegerField(choices=RETURN_PERIOD_CHOICES)
    contribution = models.FloatField()

class Event(models.Model):
    tsudat_id = models.PositiveIntegerField()
    source_zone = models.ForeignKey(SourceZone)    
    sub_faults = models.ManyToManyField(SubFault)
    magnitude = models.FloatField() # 0.0 - 10.0
    probability = models.FloatField() # 0.000001 - 1.0
    slip = models.FloatField() # in meters

    def __unicode__(self):
        return str(self.tsudat_id)

class EventWaveHeight(models.Model):
    event = models.ForeignKey(Event)
    hazard_point = models.ForeignKey(HazardPoint)
    wave_height = models.FloatField()

class Project(models.Model):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User) 
    geom = models.PolygonField()
    max_area = models.PositiveIntegerField()
    srid = models.PositiveIntegerField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return "Project ID: " + str(self.pk)

    def from_json(self, data):
        try:
            try:
                geom = GEOSGeometry(str(data.geometry))
                if(hasattr(data.geometry.crs, 'properties')):
                    crs = data.geometry.crs.properties['name']
                    srs = SpatialReference(crs)
                    geom.set_srid(srs.srid)
                    geom.transform(4326)
                ls = LineString(geom[0].coords)
                if(ls.simple == False):
                    return None, 'Error Creating Geometry: Polygon is not Valid'
                self.geom = geom
            except:
                logger.debug(sys.exc_info())
                return None, 'Error Creating Geometry'
            if('name' in data.__dict__['properties']):
                self.name = data.__dict__['properties']['name']
            else:
                return None, 'Name is required'
            if('max_area' in data.__dict__['properties']):
                try:
                    self.max_area = int(data.__dict__['properties']['max_area'])
                except ValueError:
                    return None, 'Invalid Max Area'
            else:
                return None, 'Max Area is Required'
            self.save()
            return self, None
        except:
            # ToDo catch errors specifically and return message/code
            return None, 'Unknown'

class Scenario(models.Model):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project)
    hazard_point = models.ForeignKey(HazardPoint)
    source_zone = models.ForeignKey(SourceZone)
    return_period = models.IntegerField(choices=RETURN_PERIOD_CHOICES)
    wave_height = models.FloatField() # Min 0, Max 10
    wave_height_delta = models.FloatField()
    event = models.ForeignKey(Event)
    start_time = models.PositiveIntegerField() # In Seconds Default 0 (nearly always 0)
    end_time = models.PositiveIntegerField() # In seconds
    initial_tidal_stage = models.FloatField()
    smoothing_param = models.FloatField() # Alpha
    default_friction_value = models.FloatField()
    model_setup = models.CharField(max_length=1, choices=MODEL_SETUP_CHOICES)
    raster_resolution = models.PositiveIntegerField()
    output_layers = models.ManyToManyField(ScenarioOutputLayer)
    output_max = models.BooleanField()
    use_aoi = models.BooleanField()
    tsudat_payload = models.TextField(null=True, blank=True)
    anuga_status = models.CharField(null=True, blank=True, max_length="5")
    anuga_log_message = models.TextField(null=True, blank=True)
    anuga_abort_message = models.TextField(null=True, blank=True)
    anuga_instance = models.CharField(null=True, blank=True, max_length=10)
    anuga_start_timestamp = models.DateTimeField(null=True, blank=True)
    anuga_log_timestamp = models.DateTimeField(null=True, blank=True)
    anuga_end_timestamp = models.DateTimeField(null=True, blank=True)
    anuga_payload = models.TextField(null=True, blank=True)
    tsudat_start_timestamp = models.DateTimeField(null=True, blank=True)
    tsudat_end_timestamp = models.DateTimeField(null=True, blank=True)
    map = models.ForeignKey(Map, null=True, blank=True)

    def __unicode__(self):
        return self.name

    def from_json(self, data):
        try:
            data = data['fields']
            if("name" in data):
                self.name = data['name']
            else:
                return None, "Name is Required"
            if("project" in data):
                try:
                    self.project = Project.objects.get(pk=int(data['project']))
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Project"
            else:
                return None, "Project is Required"
            if("hazard_point" in data):
                try:
                    self.hazard_point =HazardPoint.objects.get(pk=int(data['hazard_point'])) 
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Hazard Point"
            else:
                return None, "Hazard Point is Required"
            if("source_zone" in data):
                try:
                    self.source_zone = SourceZone.objects.get(pk=int(data['source_zone'])) 
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Source Zone"
            else:
                return None, "Source Zone is Required"
            if("return_period" in data):
                try:
                    self.return_period = int(data['return_period'])
                except ValueError:
                    return None, "Invalid Return Period"
            else:
                return None, "Return Period is Required"
            if("wave_height" in data):
                try:
                    self.wave_height = float(data['wave_height'])
                except ValueError:
                    return None, "Invalid Wave Height"
            else:
                return None, "Wave Height is Required"
            if("wave_height_delta" in data):
                try:
                    self.wave_height_delta = float(data['wave_height_delta'])
                except ValueError:
                    return None, "Invalid Wave Height Delta"
            else:
                return None, "Wave Height Delta is Required"
            if("event" in data):
                try:
                    self.event = Event.objects.get(pk=int(data['event'])) 
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Event"
            else:
                return None, "Event is Required"
            if("start_time" in data):
                try:
                    self.start_time = int(data['start_time'])
                except ValueError:
                    return None, "Invalid Start Time"
            else:
                #return None, "Start Time is Required"
                self.start_time = 0
            if("end_time" in data):
                try:
                    self.end_time = int(data['end_time'])
                except ValueError:
                    return None, "Invalid End Time"
            else:
                #return None, "End Time is Required"
                self.end_time = 3600
            if("initial_tidal_stage" in data):
                try:
                    self.initial_tidal_stage = float(data['initial_tidal_stage'])
                except ValueError:
                    return None, "Invalid Initial Tidal Stage"
            else:
                #return None, "Initial Tidal Stage is required"
                self.initial_tidal_stage = 0
            if("smoothing_param" in data):
                try:
                    self.smoothing_param = float(data['smoothing_param'])
                except ValueError:
                    return None, "Invalid Smoothing Param"
            else:
                #return None, "Smoothing Param Required"
                self.smoothing_param = 0.1
            if("default_friction_value" in data):
                try:
                    self.default_friction_value = float(data['default_friction_value'])
                except ValueError:
                    return None, "Invalid Default Friction Value"
            else:
                return None, "Default Friction Value Required"
            if("model_setup" in data):
                if(data['model_setup'] in ['T','B','F']):
                    self.model_setup = data['model_setup']
                else:
                    return None, "Invalid Model Setup"
            else:
                #return None, "Model Setup Required"
                self.model_setup = "T"
            if("raster_resolution" in data):
                try:
                    self.raster_resolution = int(data["raster_resolution"])
                except ValueError:
                    return None, "Invalid Raster Resolution"
            else:
                 return None, "Raster Resolution Required"
            if("output_max" in data):
                try:
                    self.output_max = data["output_max"]
                except:
                    return None, "Invalid output max"
            else:
                return None, "Output Max is required"
            if("use_aoi" in data):
                try:
                    # TODO: Verify that there is an AOI defined for this project
                    self.use_aoi = data["use_aoi"]
                except:
                    return None, "Invalid AOI Choice"
            else:
                return None, "AOI Choice is required"
            self.save()
            if("output_layers" in data):
                try:
                    layers = []
                    for layer in data["output_layers"]:
                        sol = ScenarioOutputLayer.objects.get(name=layer)
                        layers.append(sol)
                    self.output_layers = layers
                except ObjectDoesNotExist:
                    self.delete()
                    return None, "Invalid Scenario Output Layer"
            self.save()
            return self, None
        except:
            return None, 'Unknown'

class ScenarioLayer(models.Model):
    scenario = models.ForeignKey(Scenario)
    layer = models.ForeignKey(Layer)
    type = models.ForeignKey(ScenarioOutputLayer)
    ml = models.ForeignKey(MapLayer, null=True, blank=True)
    ts = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return str(self.scenario) + ' ' + str(self.layer)

class GaugePoint(models.Model):
    project = models.ForeignKey(Project)
    geom = models.PointField()
    name = models.CharField(max_length=20)

    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.project) + ' ' + self.name
    
    def from_json(self, data):
        try:
            try:
                geom = GEOSGeometry(str(data.geometry))
                if(hasattr(data.geometry.crs, 'properties')):
                    crs = data.geometry.crs.properties['name']
                    srs = SpatialReference(crs)
                    geom.set_srid(srs.srid)
                    geom.transform(4326)
                self.geom = geom
            except:
                return None, "Invalid Geometry"
            if('project_id' in data.__dict__['properties']):
                try:
                    self.project = Project.objects.get(id=int(data.__dict__['properties']['project_id']))
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Project"
            else:
                return None, "Project is required"
            if('name' in data.__dict__['properties']):
                self.name = data.__dict__['properties']['name']
            else:
                return None, "Name is Required"
            self.save()
            return self, None
        except:
            return None, "Unexpected Error"

class InternalPolygon(models.Model):
    project = models.ForeignKey(Project)
    geom = models.PolygonField()
    type = models.IntegerField(choices=IP_TYPE_CHOICES)
    value = models.FloatField(null=True, blank=True) # MR = Int MF = Float
    
    objects = models.GeoManager()
    
    def from_json(self, data):
        try:
            try:
                geom = GEOSGeometry(str(data.geometry))
                if(hasattr(data.geometry.crs, 'properties')):
                    crs = data.geometry.crs.properties['name']
                    srs = SpatialReference(crs)
                    geom.set_srid(srs.srid)
                    geom.transform(4326)
                # Topology Checks
                # - Is LinearRing (simple polygon, doesnt intersect itself)
                ls = LineString(geom[0].coords)
                if(ls.simple == False):
                    return None, 'Error Creating Geometry: Polygon is not Valid'
                self.geom = geom
            except:
                return None, "Invalid Geometry"
            if('type' in data.__dict__['properties']):
                try:
                    type = int(data.__dict__['properties']['type']) 
                    if(type in [1,2,3,4]):
                        self.type = type
                    else:
                        return None, "Invalid Type"
                except ValueError:
                    return None, "Invalid Type"
            else:
                return None, "Type is Required"
            if("project_id" in data.__dict__['properties']):
                try:
                    project_id = data.__dict__['properties']['project_id']
                    self.project = Project.objects.get(id=int(project_id))
                    # Topology Check
                    # - verify that the internal polygon is completely within the project polygon
                    if(self.project.geom.contains(self.geom) == False):
                        return None, 'Error Creating Geometry: Internal Polygon not Within Project Polygon' 
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Project"
            else:
                return None, "Project is Required"
            # Topology Check
            # - verify that the internal polygon doesnt intersect any other internal polygons for this project
            xip = InternalPolygon.objects.filter(project=self.project, geom__intersects=geom)
            if(xip.count() > 0):
                for ip in xip:
                    if(self.geom.contains(ip.geom) == False and self.geom.within(ip.geom) == False):
                        if(ip.type == 3 or self.type == 3):
                            if(self.type == 3 and ip.type == 3):
                                return None, 'Error Creating Geometry: AOI Polygons cannot intersect other AOIs' 
                        else:
                            return None, 'Error Creating Geometry: Polygon Intersects other Polygons'
            if("value" in  data.__dict__['properties']):
                try:
                    self.value = float(data.__dict__['properties']['value'])
                except ValueError:
                    return None, "Invalid Value"
            else:
                if(self.type != 3): # Value is not required for AOI
                    return None, "Value is Required"
            self.save()
            return self, None
        except:
            return None, "Unexpected Error"

class DataSet(models.Model):
    geonode_layer_uuid = models.CharField(max_length=36)
    typename = models.CharField(max_length=128, unique=True)
    data_type = models.CharField(max_length=1, choices=DATASET_TYPE_CHOICES)
    resolution = models.PositiveIntegerField() 
    geom = models.PolygonField()
    objects = models.GeoManager()
    
    def __unicode__(self):
        return str(self.pk)

class ProjectDataSet(models.Model):
    project = models.ForeignKey(Project)
    dataset = models.ForeignKey(DataSet)
    ranking = models.PositiveIntegerField() # 1 = lowest resolution -> Highest

    def from_json(self, data):
        try:
            data = data['fields']
            if('project' in data):
                try:
                    self.project = Project.objects.get(pk=int(data['project']))
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Project"
            else:
                return None, "Project Required"
            if('dataset' in data):
                try:
                    self.dataset = DataSet.objects.get(pk=int(data['dataset'])) 
                except (ValueError, ObjectDoesNotExist):
                    return None, "Invalid Dataset"
            else:
                return None, "Dataset is Required"
            if('ranking' in data):
                try:
                    self.ranking = int(data['ranking'])
                except ValueError:
                    return None, "Invalid Ranking"
            else:
                return None, "Ranking is required"
            self.save()
            return self, None
        except:
            return None, "Unexpected Error" 

class Land(models.Model):
    scalerank = models.IntegerField()
    featurecla = models.CharField(max_length=32)
    note = models.CharField(max_length=32)
    the_geom = models.MultiPolygonField(srid=4326)
    objects = models.GeoManager()

    class Meta:
        db_table = 'land_10m'
