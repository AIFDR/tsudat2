import site, os

site.addsitedir('/home/jjohnson/tsudat2/lib/python2.6/site-packages')
site.addsitedir('/home/jjohnson')
site.addsitedir('/home/jjohnson/tsudat2')
os.environ['DJANGO_SETTINGS_MODULE'] = 'tsudat2.settings'

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
