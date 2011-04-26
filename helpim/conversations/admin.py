from helpim.conversations.models import Conversation, Participant, Message
from django.utils.translation import ugettext as _
from django.contrib import admin
from django import forms
from threadedcomments.forms import ThreadedCommentForm
from django.forms.models import inlineformset_factory

CONVERSATION_EDITABLE = False

class MessageInline(admin.StackedInline):
    template = 'admin/edit_inline/with_threadedcomments.html'

    model = Message
    fieldsets = (
        (None, {
            'fields': ('sender_name', 'created_at', 'body',)
        }),
    )

    can_delete = False

    if not CONVERSATION_EDITABLE:
        readonly_fields = ('sender_name', 'created_at', 'body',)
        max_num = 0
    else:
        fieldsets[0][1]['fields'] = tuple(['sender'] + list(fieldsets[0][1]['fields']))

    verbose_name = _("Message")
    verbose_name_plural = _("Messages")

class ParticipantInline(admin.TabularInline):
    model = Participant
    can_delete = False

    if not CONVERSATION_EDITABLE:
        max_num = 0
        readonly_fields = ('name', 'role')

    verbose_name = _("Participant")
    verbose_name_plural = _("Participants")

class ConversationAdmin(admin.ModelAdmin):

    date_hierarchy = 'start_time'
    list_display = ('subject', 'start_time')


    fields = ('start_time', 'subject')

    if not CONVERSATION_EDITABLE:
        readonly_fields = ('start_time', 'subject')

    inlines = [
        ParticipantInline,
        MessageInline,
    ]

admin.site.register(Conversation, ConversationAdmin)
admin.site.disable_action('delete_selected')
