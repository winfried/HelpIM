#!/bin/sh

# Command to use when dumping the the setup for use on an other installation

`dirname $0`/manage.py dumpdata flatpages auth.group --indent 4 --natural
