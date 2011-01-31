from django.contrib.gis.db import models

# Incomplete list
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
    ('L', 'LIDAR'),
    ('S', 'SRTM'),
)

MODEL_SETUP_CHOICES = (
    ('T', 'Trial'),
    ('B', 'Basic'),
    ('F', 'Final'),
)

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
    geom = models.PolygonField()
    
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

class Scenario(models.Model):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project)
    hazard_point = models.ForeignKey(HazardPoint)
    source_zone = models.ForeignKey(SourceZone)
    return_period = models.IntegerField(choices=RETURN_PERIOD_CHOICES)
    wave_height = models.FloatField() # Min 0, Max 10
    wave_height_delta = models.PositiveIntegerField()
    event = models.ForeignKey(Event)
    start_time = models.PositiveIntegerField() # In Seconds Default 0 (nearly always 0)
    end_time = models.PositiveIntegerField() # In seconds
    initial_tidal_stage = models.FloatField()
    smoothing_param = models.FloatField() # Alpha
    default_friction_value = models.FloatField()
    model_setup = models.CharField(max_length=1, choices=MODEL_SETUP_CHOICES)

    def __unicode__(self):
        return self.name

class GaugePoint(models.Model):
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=20)
    geom = models.PointField()
    
    objects = models.GeoManager()

    def __unicode__(self):
        return self.project + ' ' + self.name

class InternalPolygon(models.Model):
    project = models.ForeignKey(Project)
    geom = models.PolygonField()
    type = models.IntegerField(choices=IP_TYPE_CHOICES)
    value = models.FloatField() # MR = Int MF = Float
    
    objects = models.GeoManager()

class DataSet(models.Model):
    # ForeignKey to geonode.Layer
    type = models.CharField(max_length=1, choices=DATASET_TYPE_CHOICES)
    resolution = models.PositiveIntegerField() 

class ProjectDataSet(models.Model):
    project = models.ForeignKey(Project)
    dataset = models.ForeignKey(DataSet)
    ranking = models.PositiveIntegerField() # 1 = lowest resolution -> Highest
