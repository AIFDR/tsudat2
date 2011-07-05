import sys
import os
import csv

sys.path.append("../")
os.environ['DJANGO_SETTINGS_MODULE'] = "tsudat2.settings"

from tsudat.utils import process_finished_simulation
from tsudat.models import Scenario

import logging, sys
for _module in ["geonode.maps.views", "geonode.maps.gs_helpers", "tsudat2.tsudat.models", "tsudat2.tsudat.views", "tsudat2.tsudat.tasks", "tsudat2.tsudat.utils"]:
   _logger = logging.getLogger(_module)
   _logger.addHandler(logging.StreamHandler(sys.stderr))
   _logger.setLevel(logging.DEBUG)

scenarios = Scenario.objects.filter(anuga_status = "STOP")

for scenario in scenarios:
    print "reprocessing completed scenario %d" % scenario.id 
    process_finished_simulation(scenario)
