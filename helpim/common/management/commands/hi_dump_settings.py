"""
Just an alias for "dumpdata" with the right models that need to be exported.
"""

from optparse import make_option

from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--indent', default=None, dest='indent', type='int',
            help='Specifies the indent level to use when pretty-printing output'),
    )
    help = 'outputs settings of an installation as json'

    def handle(self, *args, **options):
        call_command('dumpdata',
            'auth.group', # permission settings
            'flatpages', # static pages
            #'questionnaire', # questionnaires
            **options)
