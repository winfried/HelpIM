from datetime import datetime
from optparse import make_option
import sys

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from helpim.buddychat.models import BuddyChatProfile

class Command(BaseCommand):
    help = 'Sends mails to all users that need to submit recurring Questionnaires'

    option_list = BaseCommand.option_list + (
        make_option('--dry', action='store_true', dest='dry', default=False, help='Only show what would happen, do not send any mails'),
    )

    def handle(self, *args, **options):
        # process options
        self.run_dry = bool(options.get('dry', False))
        self.verbosity = int(options.get('verbosity', 1))

        # needed to build absolute URLs
        self.site = Site.objects.get_current().domain
        
        # iterate profiles
        for profile in BuddyChatProfile.objects.all():
            sent_mails = 0
            now = datetime.now()

            # check for careseeker
            if profile.needs_email_reminder('CX'):
                self.__verbose('profile "%s": needs CX' % (profile.user.username), 2)
                sent_mails += self.__send_mail('careseeker', profile)

            # check for careworker
            if profile.needs_email_reminder('SX'):
                self.__verbose('profile "%s": needs SX' % (profile.user.username), 2)
                sent_mails += self.__send_mail('careworker', profile)

            # if any mail was sent, store that date
            if sent_mails > 0:
                profile.last_email_reminder = now
                profile.save()

    def __send_mail(self, receiver_role, profile):
        '''
        Build mail text and send to role associated with profile.
        Return number of mails sent.
        '''

        # determine receipient email adress and mail text 
        if receiver_role == 'careseeker':
            subject = _('a reminder about %s' % profile.user.username)
            body = _('This is a reminder to take your next questionnaire.\n\nDon\'t reply to this message directly, reply on your personal profile page at http://%(site)s%(path_profilepage)s' % {
                'site': self.site,
                'path_profilepage': reverse('buddychat_profile', args=[profile.user.username])
            })
            rcpt = profile.user
        else:
            subject = _('a reminder about %s' % profile.user.username)
            body = _('This is a reminder to take the next questionnaire about %(careseeker)s.\n\nDon\'t reply to this message directly, reply on the personal profile page at http://%(site)s%(path_profilepage)s' % {
                'careseeker': profile.user.username,
                'site': self.site,
                'path_profilepage': reverse('buddychat_profile', args=[profile.user.username])
            })
            rcpt = profile.careworker

        # make sure email address is not empty
        if not rcpt.email:
            print >> sys.stderr, 'profile "%s": "%s" (%s) does not have an email address configured' % (profile.user.username, rcpt.username, receiver_role)
            return 0

        # abort here, if running dry
        if self.run_dry:
            self.__verbose('profile "%s": mailing "%s" (%s)' % (profile.user.username, rcpt.email, receiver_role))
            return 1

        # send mail
        self.__verbose('profile "%s": mailing "%s" (%s)' % (profile.user.username, rcpt.email, receiver_role), 2)
        rcpt.email_user(subject, body)
        return 1

    def __verbose(self, message, verbosity=1):
        '''only print message if verbosity-level is high enough'''
        if self.verbosity >= verbosity:
            print message
