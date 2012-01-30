from optparse import make_option

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
        self.verbosity = int(options.get('verbosity', 0))

        # iterate profiles
        for profile in BuddyChatProfile.objects.all():
            q = profile.needs_questionnaire_recurring('CX')
            if not q is None:
                self.__verbose('profile "%s": needs CX' % (profile.user.username), 1)
                self.__send_mail('careseeker', profile)

            q = profile.needs_questionnaire_recurring('SX')
            if not q is None:
                self.__verbose('profile "%s": needs SX' % (profile.user.username), 1)
                self.__send_mail('careworker', profile)

    def __send_mail(self, receiver_role, profile):
        # determine receipient email adress and mail text 
        if receiver_role == 'careseeker':
            subject = _('a reminder about %s' % profile.user.username)
            body = _('This is a reminder to take your next questionnaire.\n\nDon\'t reply to this message directly, reply on your personal profile page at %(url_profilepage)s' % {
                'url_profilepage': reverse('buddychat_profile', args=[profile.user.username])
            })
            rcpt = profile.user
        else:
            subject = _('a reminder about %s' % profile.user.username)
            body = _('This is a reminder to take the next questionnaire about %(careseeker)s.\n\nDon\'t reply to this message directly, reply on the personal profile page at %(url_profilepage)s' % {
                'careseeker': profile.user.username,
                'url_profilepage': reverse('buddychat_profile', args=[profile.user.username])
            })
            rcpt = profile.careworker

        # make sure email address is not empty
        if not rcpt.email:
            self.__verbose('profile "%s": "%s" (%s) does not have an email address configured' % (profile.user.username, rcpt.username, receiver_role))
            return

        # abort here, if running dry
        if self.run_dry:
            self.__verbose('profile "%s": mailing "%s" (%s)' % (profile.user.username, rcpt.email, receiver_role))
            return

        # send mail
        self.__verbose('profile "%s": mailing "%s" (%s)' % (profile.user.username, rcpt.email, receiver_role), 1)
        rcpt.email_user(subject, body)

    def __verbose(self, message, level=0):
        '''only print message if verbosity-level is high enough'''
        if level <= self.verbosity:
            print message
