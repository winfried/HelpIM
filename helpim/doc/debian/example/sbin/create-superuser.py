#!/usr/bin/env python

import os
from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth.management import create_superuser

adminpw = os.environ.get('ADMINPW')

if adminpw == '':
  print "no ADMINPW"
else:
  auth_models.User.objects.create_superuser('admin', 
         'helpdesk@e-hulp', adminpw)
