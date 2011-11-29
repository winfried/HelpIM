from os.path import dirname, join, abspath
import sys

# import default settings for this server:
sys.path.append("/etc/helpim/")
from localsettings import *

# the rest are chat-specific settings

# TIME_ZONE = 'Europe/Amsterdam'
# LANGUAGE_CODE = 'nl-NL'
# DEBUG = False

SECRET_KEY = 'SECRETKEY'

DATABASES['default']['NAME'] = 'CHATX'
DATABASES['default']['USER'] = 'CHATX'
DATABASES['default']['PASSWORD'] = 'PASSWD'

BOT['connection']['username'] = 'CHATX'
BOT['connection']['password'] = 'BOTPW'
BOT['muc']['http_domain'] = 'DOMAIN'
BOT['logging']['destination'] = 'file:/var/log/helpim/CHATX.log'

