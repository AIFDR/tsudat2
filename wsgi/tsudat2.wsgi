#! /var/www/tsudat2/wsgi/tsudat2.wsgi
import site, os
site.addsitedir('/var/www/geonode/wsgi/geonode/lib/python2.6/site-packages')
site.addsitedir('/var/www')
site.addsitedir('/var/www/tsudat2')
os.environ['DJANGO_SETTINGS_MODULE'] = 'tsudat2.settings'
from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
