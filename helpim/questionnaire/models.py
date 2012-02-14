from django.db import models
from django.dispatch import receiver, Signal
from django.utils.translation import ugettext as _

from forms_builder.forms.models import Field, Form, FormEntry

from helpim.common.models import get_position_choices
from helpim.conversations.models import Conversation


questionnaire_saved = Signal(providing_args=["questionnaire", "entry"])


class Questionnaire(Form):
    position = models.CharField(max_length=3, choices=get_position_choices(), unique=True, blank=False)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = _("Questionnaire")
        verbose_name_plural = _("Questionnaires")
        
        permissions = (
            ('can_revise_questionnaire', 'Can change answers to Questionnaires'),
        )

class ConversationFormEntry(models.Model):
    entry = models.ForeignKey(FormEntry, blank=True, null=True)
    questionnaire = models.ForeignKey(Questionnaire)
    conversation = models.ForeignKey('conversations.Conversation', blank=True, null=True)
    position = models.CharField(max_length=3, choices=get_position_choices())
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("conversation", "position"),)
        verbose_name = _("Questionnaire answer for conversation")
        verbose_name_plural = _("Questionnaire answers for conversation")

    def question_answer_dict(self):
        '''returns dictionary which maps questions to their respective answers'''
        
        result = {}

        if not self.entry:
            return result

        for answer in self.entry.fields.all():
            question = Field.objects.get(id=answer.field_id)
            result[question.label] = answer.value

        return result


@receiver(questionnaire_saved)
def save_conversation_form_entry(sender, **kwargs):
    # only "staff, on conversation type"
    if kwargs['questionnaire'].position != 'SC':
        return

    conversation = Conversation.objects.get(pk=kwargs['extra_object_id'])

    # link FormEntry and Conversation
    ConversationFormEntry.objects.create(
        entry=kwargs['entry'],
        questionnaire=kwargs['questionnaire'],
        conversation=conversation,
        position=kwargs['questionnaire'].position
    )


from helpim.questionnaire.fields import register_forms_builder_field_type, ScaleField, ScaleWidget, DoubleDropField, DoubleDropWidget
register_forms_builder_field_type(100, _('Scale'), ScaleField, ScaleWidget)
register_forms_builder_field_type(101, _('Double droplist'), DoubleDropField, DoubleDropWidget)
