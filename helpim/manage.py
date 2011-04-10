#!/usr/bin/env python

import os, sys

# make sure we use the Django version included in the HelpIM tree (if
# any), fall back to the os-wide installed version of Django
gitPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
djangoPath = os.path.join(gitPath, "vendor", "django")
if os.path.exists(djangoPath) and not djangoPath in sys.path:
    sys.path = [djangoPath]+sys.path

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)
