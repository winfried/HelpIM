from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from forms_builder.forms.models import Form, FormEntry

POSITION_CHOICES = (
  ('CB', _('Client, before chat')),
  ('CA', _('Client, after chat')),
  ('SA', _('Staff, after chat')),
  ('SC', _('Staff, on Conversation page')),
)

class Questionnaire(Form):

    position = models.CharField(max_length=3, choices=POSITION_CHOICES, unique=True, blank=False)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = _("Questionnaire")
        verbose_name_plural = _("Questionnaires")
        
        permissions = (
            ('can_revise_questionnaire', 'Can change answers to Questionnaires')
        )

class ConversationFormEntry(models.Model):
    entry = models.ForeignKey(FormEntry, blank=True, null=True)
    questionnaire = models.ForeignKey(Questionnaire)
    conversation = models.ForeignKey('conversations.Conversation', blank=True, null=True)
    position = models.CharField(max_length=3, choices=POSITION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("conversation", "position"),)
        verbose_name = _("Questionnaire answer for conversation")
        verbose_name_plural = _("Questionnaire answers for conversation")

from helpim.questionnaire.fields import register_forms_builder_field_type, ScaleField, ScaleWidget, DoubleDropField, DoubleDropWidget
register_forms_builder_field_type(100, _('Scale'), ScaleField, ScaleWidget)
register_forms_builder_field_type(101, _('Double droplist'), DoubleDropField, DoubleDropWidget)
