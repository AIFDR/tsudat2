import sys
import os
import csv

sys.path.append("../")
os.environ['DJANGO_SETTINGS_MODULE'] = "tsudat2.settings"

from django.contrib.auth.models import User
from geonode.maps.models import Contact


participants = csv.reader(open('data/participant_list.csv', 'ro'))
for participant in participants:
    name = participant[2]
    first_name = name.split(' ')[0]
    last_name = name.split(' ')[1]
    print name, first_name, last_name
    email = participant[5].lower()
    password = participant[10]
    username = name.replace(' ', '').lower()

    jurisdiction = participant[3]
    organization = participant[4]
    
    new_user = User.objects.create_user(username, email, password)
    new_user.first_name = first_name
    new_user.last_name = last_name
    new_user.save()
    new_contact = Contact(user=new_user, name=name, organization=organization, email=email)
    new_contact.save()
