from django.contrib import admin
from django.utils.translation import ugettext as _
from forms_builder.forms.admin import FormAdmin
from helpim.questionnaire.models import Questionnaire, ConversationFormEntry

class QuestionnaireAdmin(FormAdmin):
    fieldsets = [(
      _("HelpIM"), {
        "fields": ("position",),
      })] + FormAdmin.fieldsets
    list_display = ["position"] + list(FormAdmin.list_display)

admin.site.register(Questionnaire, QuestionnaireAdmin)
admin.site.register(ConversationFormEntry)

