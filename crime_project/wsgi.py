"""
WSGI config for crime_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For cPanel Passenger deployment, use the ``passenger_wsgi.py`` file instead,
or set the Passenger WSGI entry point in cPanel to ``crime_project.wsgi:application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crime_project.settings")

application = get_wsgi_application()
