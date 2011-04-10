from helpim.conversations.models import Conversation, Participant
from django.utils.translation import ugettext as _
from django.contrib import admin

class ParticipantInline(admin.TabularInline):
    model = Participant
    readonly_fields = ('name',)
    can_delete = False
    max_num = 0

    verbose_name = _("Participant")
    verbose_name_plural = _("Participants")

class ConversationAdmin(admin.ModelAdmin):

    date_hierarchy = 'start_time'
    list_display = ('subject', 'start_time')


    fields = ('start_time', 'subject')
    readonly_fields = ('start_time', 'subject')

    inlines = [
        ParticipantInline,
    ]

admin.site.register(Conversation, ConversationAdmin)
admin.site.disable_action('delete_selected')
