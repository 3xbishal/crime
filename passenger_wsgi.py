"""
Passenger WSGI entry point for cPanel deployment.

This file is used by cPanel's Passenger application to serve the Django app.
Set the Passenger WSGI entry point in cPanel to:
    passenger_wsgi.py:application

For Apache configuration in cPanel, you can also add the following
to your .htaccess file:

    PassengerAppRoot /home/username/path/to/crime
    PassengerPython /usr/local/bin/python3
    PassengerAppType wsgi
    PassengerStartupFile passenger_wsgi.py

If using a virtual environment, point PassengerPython to the venv Python:
    PassengerPython /home/username/path/to/crime/venv/bin/python3
"""

import os
import sys

# Add the project directory to the Python path
# Adjust this path to match your cPanel setup
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crime_project.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
