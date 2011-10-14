from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from helpim.conversations.models import Conversation
from forms_builder.forms.models import Form, FormEntry

POSITION_CHOICES = (
  ('CB', _('Client, before chat')),
  ('CA', _('Client, after chat')),
  ('SA', _('Staff, after chat')),
)

class Questionnaire(Form):

    position = models.CharField(max_length=3, choices=POSITION_CHOICES, unique=True, blank=False)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = _("Questionnaire")
        verbose_name_plural = _("Questionnaires")

class ConversationFormEntry(models.Model):
    entry = models.ForeignKey(FormEntry)

    conversation = models.ForeignKey(Conversation, blank=False)
    position = models.CharField(max_length=3, choices=POSITION_CHOICES, blank=False)

    class Meta:
        unique_together = (("conversation", "position"),)
        verbose_name = _("Questionnaire answer for conversation")
        verbose_name_plural = _("Questionnaire answers for conversation")

