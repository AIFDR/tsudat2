 source /var/lib/geonode/bin/activate
export PATH=$PATH:/usr/pgsql-9.0/bin/
pip install django-celery
pip install -e git+git://github.com/jtauber/django-notification.git#egg=django_notification
pip install django-kombu
pip install geojson
pip install vectorformats
pip install wadofstuff-django-serializers 
pip install psycopg2
pip install -e git+git://github.com/ericflo/django-pagination.git#egg=django_pagination
pip install pytz
pip install django-timezones
