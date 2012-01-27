from datetime import datetime, timedelta

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

""" check if we're loaded before helpim.rooms and helpim.questionnaires """
from django.conf import settings
ia = settings.INSTALLED_APPS
if ia.index('helpim.buddychat') > ia.index('helpim.rooms') or ia.index('helpim.buddychat') > ia.index('helpim.questionnaire'):
    raise ConfigurationError('bad order of INSTALLED_APPS: helpim.buddychat must be loaded before helpim.questionnaire and helpim.rooms')

from helpim.common.models import register_position_choices
register_position_choices([
  ('CR', _('Client, after Registration')),
  ('CA', _('Client, after chat')),
  ('SA', _('Staff, after chat')),
  ('CX', _('Client, recurring')),
  ('SX', _('Staff, recurring')),
])

from helpim.conversations.models import Conversation, Chat
from helpim.questionnaire.models import Questionnaire
from helpim.questionnaire.views import questionnaire_done
from helpim.rooms.models import SimpleRoom
from forms_builder.forms.models import FormEntry
from helpim.common.models import get_position_choices

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
        Decide whether this profile must take the recurring Questionnaire.
        There are two types of such a Questionnaire: one for the careseeker (CX) and one for the careworker(SX)
        If so, return a reference to that Questionnaire. If not, return None.
        '''
        # only continue if coupled with a careworker
        if self.is_coupled() is False:
            return None

        # dont continue if there is no recurring questionnaire configured
        try:
            q_recurring = Questionnaire.objects.filter(position=position)[0]
        except IndexError:
            q_recurring = None
        if q_recurring is None:
            return None

        # get the latest recurring questionnaire taken by this user to check if its ago long enough for the user to take another one.
        # if the user has never taken a recurring questionnaire, compare against the date when he was coupled.
        latest_cx = self.get_latest_questionnaire_entry(position)
        if latest_cx is None:
            compare_against = self.coupled_at
        else:
            compare_against = latest_cx.created_at

        # has enough time passed?
        if compare_against + timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL) <= datetime.now():
            return q_recurring
        else:
            return None

    class Meta:
        verbose_name = _("Chat Buddy")
        verbose_name_plural = _("Chat Buddies")
        permissions = (
            ('is_coordinator', 'Is allowed to coordinate careworkers & careseekers'),
            ('is_careworker', 'Is a careworker')
            )

class QuestionnaireFormEntry(models.Model):
    entry = models.ForeignKey(FormEntry, blank=True, null=True)
    questionnaire = models.ForeignKey(Questionnaire)
    buddychat_profile = models.ForeignKey(BuddyChatProfile, related_name='questionnaires')
    position = models.CharField(max_length=3, choices=get_position_choices())
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Questionnaire answer")
        verbose_name_plural = _("Questionnaire answers")

@receiver(questionnaire_done)
def save_q_form_entry(sender, **kwargs):
    profile = BuddyChatProfile.objects.get(user=sender.user)
    q_form_entry = QuestionnaireFormEntry(questionnaire=kwargs['questionnaire'],
                                          position=kwargs['questionnaire'].position,
                                          buddychat_profile=profile,
                                          entry=kwargs['entry'])
    q_form_entry.save()
    profile.ready = True
    profile.save()
