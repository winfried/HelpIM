from datetime import datetime

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

from helpim.conversations.models import Conversation
from helpim.questionnaire.models import Questionnaire
from helpim.questionnaire.views import questionnaire_done
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

    objects = BuddyChatProfileManager()

    class Meta:
        verbose_name = _("Chat Buddy")
        verbose_name_plural = _("Chat Buddies")
        permissions = (
            ('is_coordinator', 'Is allowed to coordinate careworkers and careseekers'),
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
                                          buddychat_profile=profile,
                                          entry=kwargs['entry'])
    q_form_entry.save()
    profile.ready = True
    profile.save()
