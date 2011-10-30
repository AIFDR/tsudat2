import sys, os

sys.path.append("../")
sys.path.append("./")
os.environ['DJANGO_SETTINGS_MODULE'] = "tsudat2.settings"

from geonode.maps.utils import upload 
from django.contrib.auth.models import User

u = User.objects.get(pk=1)
print u

upload('/home/tsudat/temp', u)
