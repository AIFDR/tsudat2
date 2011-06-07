source ../geonode/wsgi/geonode/bin/activate
export PATH=$PATH:/usr/pgsql-9.0/bin/
pip install django-celery
pip install django-notification
pip install django-kombu
pip install geojson
pip install vectorformats
pip install wadofstuff-django-serializers 
pip install psycopg2
