from django.contrib.gis import admin
from tsudat.models import *

class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'project', 'anuga_status', 'anuga_instance', 'tsudat_start_timestamp', 'anuga_start_timestamp', 'anuga_end_timestamp','tsudat_end_timestamp')
    list_filter = ('anuga_status',)
    search_fields = ('name',)

admin.site.register(HazardPoint, admin.OSMGeoAdmin)
admin.site.register(HazardPointDetail, admin.ModelAdmin)
admin.site.register(SourceZone, admin.OSMGeoAdmin)
admin.site.register(Event, admin.ModelAdmin)
admin.site.register(Project, admin.OSMGeoAdmin)
admin.site.register(Scenario, ScenarioAdmin)
admin.site.register(GaugePoint, admin.OSMGeoAdmin)
admin.site.register(InternalPolygon, admin.OSMGeoAdmin)
admin.site.register(DataSet, admin.OSMGeoAdmin)
admin.site.register(ProjectDataSet, admin.ModelAdmin)
admin.site.register(SubFault, admin.OSMGeoAdmin)
admin.site.register(ScenarioOutputLayer, admin.ModelAdmin)
admin.site.register(Land, admin.OSMGeoAdmin)
