#!/bin/sh

# Command to use when dumping the the setup for use on an other installation
# Usage:
#
# dump_setup_data.sh > django/helpim/fixtures/setup_data.json

python django/helpim/manage.py dumpdata flatpages auth.group --indent 4 --natural

