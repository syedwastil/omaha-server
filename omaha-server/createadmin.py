#!/usr/bin/env python
# coding: utf8

import django
import os
from dotenv import load_dotenv
django.setup()
load_dotenv()
from django.contrib.auth import get_user_model

User = get_user_model()

if User.objects.count() == 0:
    admin = User.objects.create(username=os.getenv('ADMIN_USER'), email='admin@example.com',
                                first_name='Admin', last_name='Admin')
    admin.set_password(os.getenv('ADMIN_PASSWORD'))
    admin.is_superuser = True
    admin.is_staff = True
    admin.save()
