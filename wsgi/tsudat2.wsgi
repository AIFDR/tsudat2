import site, os
os.environ["CELERY_LOADER"] = "django"
os.environ['DJANGO_SETTINGS_MODULE'] = 'tsudat2.settings'
site.addsitedir('/usr/src')
site.addsitedir('/usr/src/tsudat2')
from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
