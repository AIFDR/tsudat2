# Django settings for tsudat2 project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SERVE_MEDIA = True

SITEURL = "http://tsudat.dev.opengeo.org/"

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'tsudat',                      # Or path to database file if using sqlite3.
        'USER': 'tsudat',                      # Not used with sqlite3.
        'PASSWORD': 'tsudat',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
    'geonode': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'geonode',                      # Or path to database file if using sqlite3.
        'USER': 'geonode',                      # Not used with sqlite3.
        'PASSWORD': 'BedxfLPt',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '5432',                      # Set to empty string for default. Not used with sqlite3.
    }
}

GEOSERVER_BASE_URL="http://localhost:8080/geoserver-geonode-dev/"
GEOSERVER_CREDENTIALS = "admin", "geoserver" 
GEONETWORK_BASE_URL = SITEURL + "geonetwork/"
GEONETWORK_CREDENTIALS = "admin", 'admin'


PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(28f@wmx0qnm#=_1$vxu7l55vvovt$e!2f@++%6$)i2i3erb@z'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'tsudat2.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT,"templates"),
)


STATIC_ROOT = os.path.abspath(os.path.dirname(__file__))
#STATIC_ROOT = os.path.join(PROJECT_ROOT,"media")

STATIC_URL = '/static/'

STATICFILES_DIRS = (
        os.path.join(PROJECT_ROOT, 'media/'),
        os.path.join(PROJECT_ROOT, 'externals/openlayers/'),
        os.path.join(PROJECT_ROOT, 'externals/geoext/'),
        os.path.join(PROJECT_ROOT, 'externals/gxp/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.gis',
    'staticfiles',
    'proxy',
    'tsudat',
    'geonode.maps',
)
