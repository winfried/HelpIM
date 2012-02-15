from datetime import datetime, timedelta
from functools import partial

from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.utils.translation import ugettext as _

from registration.models import RegistrationProfile, RegistrationManager

class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

""" if helpim.buddychat is loaded, require we're loaded before helpim.rooms and helpim.questionnaires """
from django.conf import settings
ia = settings.INSTALLED_APPS
if 'helpim.buddychat' in ia:
    if ia.index('helpim.buddychat') > ia.index('helpim.rooms') or ia.index('helpim.buddychat') > ia.index('helpim.questionnaire'):
        raise ConfigurationError('bad order of INSTALLED_APPS: helpim.buddychat must be loaded before helpim.questionnaire and helpim.rooms')

from helpim.common.models import register_position_choices
register_position_choices([
  ('CR', _('Client, after Registration')),
  ('CA', _('Client, after chat')),
  ('SA', _('Staff, after chat')),
  ('SC', _('Staff, on Conversation page')),
  ('CX', _('Client, recurring')),
  ('SX', _('Staff, recurring')),
])

from helpim.common.models import get_position_choices
from helpim.conversations.models import Conversation, Chat
from helpim.questionnaire.models import Questionnaire, questionnaire_saved
from helpim.rooms.models import SimpleRoom
from forms_builder.forms.models import FormEntry

class BuddyChatProfileManager(RegistrationManager):
    def create(self, user, activation_key):
        now = datetime.now()
        conv1 = Conversation(start_time=now); conv1.save()
        conv2 = Conversation(start_time=now); conv2.save()
        conv3 = Conversation(start_time=now); conv3.save()
        profile = BuddyChatProfile(
            user = user,
            activation_key = activation_key,
            careworker_conversation = conv1,
            coordinator_conversation = conv2,
            careworker_coordinator_conversation = conv3,
            )
        profile.save()
        return profile

class BuddyChatProfile(RegistrationProfile):

    '''set to True after CR questionnaire was taken'''
    ready = models.BooleanField(default=False)
    careworker = models.ForeignKey(User,
                                  verbose_name=_("Careworker"),
                                  blank=True,
                                  null=True,
                                  limit_choices_to = {'groups__name': 'careworkers'},
        )

    coupled_at = models.DateTimeField(blank=True, null=True)

    careworker_conversation = models.ForeignKey(Conversation, related_name='+')
    coordinator_conversation = models.ForeignKey(Conversation, related_name='+')
    careworker_coordinator_conversation = models.ForeignKey(Conversation, related_name='+')

    room = models.ForeignKey(SimpleRoom, blank=True, null=True)

    last_email_reminder = models.DateTimeField(editable=False, default=partial(datetime.fromtimestamp, 0))

    objects = BuddyChatProfileManager()

    def chats(self):
        return [chat for chat in Chat.objects.filter(participant__user = self.user) if chat.messages.count() > 0]

    def is_coupled(self):
        return not self.careworker is None

    def get_latest_questionnaire_entry(self, position):
        '''
        returns the latest QuestionnaireFormEntry for this profile of given position or None if no such object exists.
        '''
        try:
            return self.questionnaires.filter(position=position).order_by('-created_at')[0]
        except IndexError:
            return None

    def unread_messages_coordinator(self):
        '''return QuerySet of unread messages for coordinator role'''

        # messages careseeker -> coordinator
        from_careseeker = self.coordinator_conversation.messages.filter(read=False, sender__user=self.user)

        # messages careworker -> coordinator
        from_careworker = self.careworker_coordinator_conversation.messages.filter(read=False, sender__user=self.careworker)

        # combine QuerySets
        return from_careseeker | from_careworker

    def unread_messages_careworker(self):
        '''return QuerySet of unread messages for careworker role'''

        # messages careseeker -> careworker
        from_careseeker = self.careworker_conversation.messages.filter(read=False, sender__user=self.user)

        # messages coordinator -> careworker
        # in careworker_coordinator_conversation: (not careworker) => sender is coordinator
        from_coordinator = self.careworker_coordinator_conversation.messages.exclude(sender__user=self.careworker).filter(read=False)

        # combine QuerySets
        return from_careseeker | from_coordinator

    def unread_messages_careseeker(self):
        '''return QuerySet of unread messages for careseeker role'''
        
        # messages careworker -> careseeker
        from_careworker = self.careworker_conversation.messages.exclude(sender__user=self.user).filter(read=False)
        
        # messages coordinator -> careseeker
        from_coordinator = self.coordinator_conversation.messages.exclude(sender__user=self.user).filter(read=False)
        
        # combine QuerySets
        return from_careworker | from_coordinator
    
    def needs_questionnaire_CR(self):
        '''
        Decide whether this profile must take the CR questionnaire.
        If so, return a reference to that Questionnaire. If not, return None.
        '''
        q = None

        if not self.ready:
            try:
                q = Questionnaire.objects.filter(position='CR')[0]
            except IndexError:
                pass

        return q

    def needs_questionnaire_recurring(self, position):
        '''
        Decide whether this profile must take a recurring Questionnaire.
        There are two types of such a Questionnaire: one for the careseeker (CX) and one for the careworker(SX).
        If so, return a reference to that Questionnaire. If not, return None.
        '''

        # only continue if coupled with a careworker
        if self.is_coupled() is False:
            return None, None

        # dont continue if there is no recurring questionnaire configured
        try:
            q_recurring = Questionnaire.objects.filter(position=position)[0]
        except IndexError:
            q_recurring = None
        if q_recurring is None:
            return None, None

        # from the point 'coupled_at + RECURRING_QUESTIONNAIRE_INTERVAL' on, (this first interval is covered by CR-Questionnaire)
        # there are time slots of length RECURRING_QUESTIONNAIRE_INTERVAL in each of which careseeker/careworker can submit one CX/SX-Questionnaire
        # find the starting datetime of the currently running interval
        interval = timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL)
        now = datetime.now()
        current_interval_start = self.coupled_at

        # this will run at least once, because coupled_at will always be in the past
        # after the loop, current_interval_start will be > now (in the future), fix that
        while current_interval_start <= now:
            current_interval_start += interval
        current_interval_start -= interval

        # at least one interval must have passed
        if current_interval_start <= self.coupled_at:
            return None, current_interval_start

        # in the current interval, was there already a Questionnaire submission?
        if self.questionnaires.filter(position=position, created_at__gte=current_interval_start).count() > 0:
            return None, current_interval_start
        else:
            return q_recurring, current_interval_start
        
    def needs_email_reminder(self, position):
        '''
        Returns True if an email notification about a recurring Questionnaire should be sent
        '''

        (q, interval_start) = self.needs_questionnaire_recurring(position)

        if q is None or interval_start is None:
            return False

        interval = timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL)
        now = datetime.now()

        # a new interval has started and no reminder was sent since current interval started
        if now <= interval_start and self.last_email_reminder < interval_start:
            return True

        # at least 20% of interval length has passed since last reminder
        if now >= (self.last_email_reminder + interval / 5):
            return True

        return False

    class Meta:
        verbose_name = _("Chat Buddy")
        verbose_name_plural = _("Chat Buddies")
        permissions = (
            ('is_coordinator', 'Is allowed to coordinate careworkers & careseekers'),
            ('is_careworker', 'Is a careworker')
            )

class QuestionnaireFormEntryManager(models.Manager):
    def for_profile_and_user(self, profile, user):
        '''only return objects which given User is allowed to see on given profile'''

        all_questionnaires = self.filter(buddychat_profile=profile)

        # coordinator role can see all questionnaires to a profile
        if user.has_perm('buddychat.is_coordinator'):
            return all_questionnaires

        # careworker can see questionnaires of type SX if he is careworker of that profile
        if profile.careworker == user and user.has_perm('buddychat.is_careworker'):
            return all_questionnaires.filter(buddychat_profile__careworker=user, position='SX')

        # careseeker can see questionnaires of types CR,CA,CR of owned profile
        if profile.user == user:
            return all_questionnaires.filter(buddychat_profile__user=user, position__in=['CR', 'CA', 'CX'])

        return []

class QuestionnaireFormEntry(models.Model):
    entry = models.ForeignKey(FormEntry, blank=True, null=True)
    questionnaire = models.ForeignKey(Questionnaire)
    buddychat_profile = models.ForeignKey(BuddyChatProfile, related_name='questionnaires')
    position = models.CharField(max_length=3, choices=get_position_choices())
    created_at = models.DateTimeField(auto_now_add=True)

    objects = QuestionnaireFormEntryManager()
    
    class Meta:
        verbose_name = _("Questionnaire answer")
        verbose_name_plural = _("Questionnaire answers")


@receiver(questionnaire_saved)
def save_q_form_entry(sender, **kwargs):
    # only "staff, recurring"
    if not kwargs['questionnaire'].position in ['CR', 'CX', 'SX']:
        return

    profile = BuddyChatProfile.objects.get(pk=kwargs['extra_object_id'])
    q_form_entry = QuestionnaireFormEntry(entry=kwargs['entry'],
                                          questionnaire=kwargs['questionnaire'],
                                          buddychat_profile=profile,
                                          position=kwargs['questionnaire'].position)
    q_form_entry.save()
    profile.ready = True
    profile.save()
