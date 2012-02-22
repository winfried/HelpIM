from os.path import dirname, join, abspath
import sys

# import default settings for this server:
sys.path.append("/etc/helpim/")
from localsettings import *

# the rest are chat-specific settings

# TIME_ZONE = 'Europe/Amsterdam'
# LANGUAGE_CODE = 'nl-NL'
# BOT['language'] = 'nl-nl'
# DEBUG = False
# CHAT['staff_muc_nick'] = 'CHATX'

SECRET_KEY = 'SECRETKEY'

DATABASES['default']['NAME'] = 'CHATX'
DATABASES['default']['USER'] = 'CHATX'
DATABASES['default']['PASSWORD'] = 'PASSWD'

BOT['connection']['username'] = 'CHATX'
BOT['connection']['password'] = 'BOTPW'
BOT['muc']['http_domain'] = 'https://DOMAINX'
BOT['logging']['destination'] = 'file:/var/log/helpim/CHATX.log'

# Use the two options to set the name and domain of your default Site.
# The Site object will be created during 'syncdb'.
SITE_DOMAIN = 'DOMAINX'
SITE_NAME = 'DOMAINX'
