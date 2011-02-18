from django.contrib.gis import admin
from tsudat.models import *

admin.site.register(HazardPoint, admin.OSMGeoAdmin)
admin.site.register(HazardPointDetail, admin.ModelAdmin)
admin.site.register(SourceZone, admin.OSMGeoAdmin)
admin.site.register(Event, admin.ModelAdmin)
admin.site.register(Project, admin.OSMGeoAdmin)
admin.site.register(Scenario, admin.ModelAdmin)
admin.site.register(GaugePoint, admin.OSMGeoAdmin)
admin.site.register(InternalPolygon, admin.OSMGeoAdmin)
admin.site.register(DataSet, admin.OSMGeoAdmin)
admin.site.register(ProjectDataSet, admin.ModelAdmin)
admin.site.register(SubFault, admin.OSMGeoAdmin)
