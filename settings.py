# Django settings for tsudat2 project.
import os
from urllib import urlencode
import geonode

_ = lambda x: x

SITENAME = "TsuDAT"
SITEURL = "http://tsudat.nci.org.au/"

DEBUG = TEMPLATE_DEBUG = True 
MINIFIED_RESOURCES = True
SERVE_MEDIA = True

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
GEONODE_ROOT = os.path.dirname(geonode.__file__)

ADMINS = (
    ('Jeffrey Johnson', 'jjohnson@opengeo.org'),
)

MANAGERS = ADMINS

ROOT_URLCONF = 'tsudat2.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'tsudat',                      # Or path to database file if using sqlite3.
        'USER': 'tsudat',                      # Not used with sqlite3.
        'PASSWORD': 'tsudat',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
	'SUPPORTS_TRANSACTIONS': 'True',
    },
}

SERIALIZATION_MODULES = {
    'json': 'wadofstuff.django.serializers.json'
}

GEOSERVER_BASE_URL = SITEURL + "geoserver-geonode-dev/"
GEOSERVER_CREDENTIALS = "admin", "geoserver" 

GEONETWORK_BASE_URL = SITEURL + "geonetwork/"
GEONETWORK_CREDENTIALS = "admin", 'admin'

TSUDAT_BASE_DIR='/tmp/tsudat'
TSUDAT_MUX_DIR='/data_area/Tsu-DAT_1.0/Tsu-DAT_Data/earthquake_data'

# Celery Settings
CARROT_BACKEND = "django"
CELERY_IMPORTS = ("tsudat2.tsudat.tasks", )
CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_DBURI = "postgresql://tsudat:tsudat@localhost/tsudat"
CELERYD_LOG_LEVEL = "DEBUG"
#CELERY_ALWAYS_EAGER = True
#CELERY_SEND_EVENTS = True

import djcelery
djcelery.setup_loader()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Australia/Sydney'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html

LANGUAGE_CODE = 'en'

LANGUAGES = (
    ('en', _('English')),
    ('es', _('Spanish')),
)

SITE_ID = 1

# Setting a custom test runner to avoid running the tests for some problematic 3rd party apps
TEST_RUNNER='geonode.testrunner.GeoNodeTestRunner'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "site_media", "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = SITEURL + "media/"

# Absolute path to the directory that holds static files like app media.
# Example: "/home/media/media.lawrence.com/apps/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, "site_media", "static")

# URL that handles the static files like app media.
# Example: "http://media.lawrence.com"
STATIC_URL = "/media/"

GEONODE_UPLOAD_PATH = os.path.join(STATIC_URL, "upload/")
GEONODE_CLIENT_LOCATION = SITEURL + 'media/static/'

# Additional directories which hold static files
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, "media"),
]

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX="/admin-media/"

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'myv-y4#7j-d*p-__@j#*3z@!y24fz8%^z2v6atuy4bo9vqr1_a'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "geonode.maps.context_processors.resource_urls",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

# This isn't required for running the geonode site, but it when running sites that inherit the geonode.settings module.
LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, "locale"),
    os.path.join(PROJECT_ROOT, "maps", "locale"),
)

# Note that Django automatically includes the "templates" dir in all the
# INSTALLED_APPS, se there is no need to add maps/templates or admin/templates
TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT,"templates"),
    os.path.join(GEONODE_ROOT, 'templates'),
)

AUTHENTICATION_BACKENDS = ('geonode.core.auth.GranularBackend',)

GOOGLE_API_KEY = ""
LOGIN_REDIRECT_URL = "/"

DEFAULT_LAYERS_OWNER='admin'

# Where should newly created maps be focused?
DEFAULT_MAP_CENTER = (-84.7, 12.8)

# How tightly zoomed should newly created maps be?
# 0 = entire world;
# maximum zoom is between 12 and 15 (for Google Maps, coverage varies by area)
DEFAULT_MAP_ZOOM = 7

MAP_BASELAYERSOURCES = {
    "any": {
        "ptype":"gx_olsource"
    },
    "capra": {
        "url":"/geoserver/wms"
    },
    "google":{
        "ptype":"gx_googlesource",
        "apiKey": GOOGLE_API_KEY
    }
}

MAP_BASELAYERS = [{
    "source":"any",
    "type":"OpenLayers.Layer",
    "args":["No background"],
    "visibility": False,
    "fixed": True,
    "group":"background"
  },{
    "source":"any",
    "type":"OpenLayers.Layer.OSM",
    "args":["OpenStreetMap"],
    "visibility": True,
    "fixed": True,
    "group":"background"
  },{
    "source":"any",
    "type":"OpenLayers.Layer.WMS",
    "group":"background",
    "visibility": False,
    "fixed": True,
    "args":[
      "bluemarble",
      "http://maps.opengeo.org/geowebcache/service/wms",
      {
        "layers":["bluemarble"],
        "format":"image/png",
        "tiled": True,
        "tilesOrigin":[-20037508.34,-20037508.34]
      },
      {"buffer":0}
    ]
  },{
    "source":"google",
    "group":"background",
    "name":"SATELLITE",
    "visibility": False,
    "fixed": True,
}]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.gis',
    'geonode.maps',
    'geonode.core',
    'geonode.proxy',
    'profiles',
    'notification',
    'staticfiles',
    'tsudat',
    'djcelery',
    'djkombu',
    'django_extensions',
    'registration',
    'avatar',
)

def get_user_url(u):
    from django.contrib.sites.models import Site
    s = Site.objects.get_current()
    return "http://" + s.domain + "/profiles/" + u.username

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': get_user_url
}

AUTH_PROFILE_MODULE = 'maps.Contact'
REGISTRATION_OPEN = False

try:
    from local_settings import *
except ImportError:
    pass

import logging, sys
for _module in ["geonode.maps.views", "geonode.maps.gs_helpers", "tsudat2.tsudat.tasks"]:
   _logger = logging.getLogger(_module)
   _logger.addHandler(logging.StreamHandler(sys.stderr))
   _logger.setLevel(logging.DEBUG)
