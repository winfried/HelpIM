from os.path import dirname, join, abspath

# import settings from egg:
# see: /usr/local/lib/python2.6/dist-packages/helpim/settings.py
from helpim.settings import *


# the rest are default settings for this server

TIME_ZONE = 'Europe/Amsterdam'
LANGUAGE_CODE = 'nl-NL'
BOT['language'] = 'nl-nl'
STATIC_ROOT = ''
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'
FORMS_BUILDER_USE_SITES = False
SERVER_EMAIL = 'root@xen9.vandervlis.nl'
SEND_BROKEN_LINK_EMAILS = True

ADMINS = (
     ('Helpdesk', 'helpdesk@e-hulp.nl'),
)

FIXTURE_DIRS = (
   abspath(join(dirname('/usr/local/share/helpim/'), 'fixtures')),
)

STATICFILES_DIRS = (
    ("xmpptk", abspath(join(dirname(__file__), '..', 'parts', 'xmpptk', 'htdocs'))),
    ("javascript", abspath(join(dirname(__file__), 'javascript', 'htdocs'))),
)

TEMPLATE_DIRS = (
    abspath(join(dirname('/usr/local/share/helpim/'), 'templates')),
)

LOCALE_PATHS = (
    '/usr/local/share/helpim/locale',
)
