from helpim.conversations.models import Conversation, Participant, ChatMessage
from django.utils.translation import ugettext as _
from django.contrib import admin
from django import forms
from threadedcomments.forms import ThreadedCommentForm
from django.forms.models import inlineformset_factory
from django.conf import settings

CONVERSATION_EDITABLE = False

class MessageInline(admin.StackedInline):
    template = 'admin/edit_inline/with_threadedcomments.html'

    fieldsets = (
        (None, {
            'fields': ('sender_name', 'time_sent', 'body', 'event')
        }),
    )

    can_delete = False

    if not CONVERSATION_EDITABLE:
        readonly_fields = ('sender_name', 'time_sent', 'body', 'event')
        max_num = 0
    else:
        fieldsets[0][1]['fields'] = tuple(['sender'] + list(fieldsets[0][1]['fields']))

    verbose_name = _("Message")
    verbose_name_plural = _("Messages")

class ChatMessageInline(MessageInline):
    model = ChatMessage

class ParticipantInline(admin.TabularInline):
    template = 'admin/edit_inline/with_block_button.html'

    model = Participant
    can_delete = False

    max_num = 0
    readonly_fields = ('name', 'role')
    fields = ('name', 'role', 'blocked')

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
        ChatMessageInline,
    ]

    def get_changelist(self, request, **kwargs):
        ChangeList = super(ConversationAdmin, self).get_changelist(request, **kwargs)

        class SelectList(ChangeList):
            def __init__(self, *args, **kwargs):
                super(SelectList, self).__init__(*args, **kwargs)
                self.title = _("Conversations")

        return SelectList

    def queryset(self, request):
        qs = super(ConversationAdmin, self).queryset(request)

        restrict_to_own_conversations = getattr(settings,
            "HELPIM_RESTRICT_VOLUNTEER_TO_OWN_CONVERSATIONS", False
        )

        if (not restrict_to_own_conversations) or request.user.is_superuser:
            return qs
        else:
            return qs.filter(
                     participant__name=request.user.username,
                     participant__role=Participant.ROLE_STAFF
                   )


admin.site.register(Conversation, ConversationAdmin)
admin.site.disable_action('delete_selected')
