from helpim.common.models import AdditionalUserInformation
from helpim.conversations.models import Conversation, Participant, ChatMessage
from django.utils.translation import ugettext as _
from django.contrib import admin
from django import forms
from threadedcomments.forms import ThreadedCommentForm
from django.forms.models import inlineformset_factory
from django.conf import settings

CONVERSATION_EDITABLE = False
from forms_builder.forms.models import FormEntry
from helpim.questionnaire.models import ConversationFormEntry

from helpim.conversations.widgets import IframeReadonlyWidget

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

    if not CONVERSATION_EDITABLE:
        max_num = 0
        readonly_fields = ('name', 'role')
        can_delete = False

    fields = ['name', 'role', 'blocked']

    if CONVERSATION_EDITABLE:
        fields += ['user']

    verbose_name = _("Participant")
    verbose_name_plural = _("Participants")

class ConversationFormEntryInline(admin.StackedInline):

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'entry':
            kwargs['widget'] = IframeReadonlyWidget
            return super(admin.StackedInline, self).formfield_for_dbfield(db_field,**kwargs)

    model = ConversationFormEntry
    readonly_fields = ('position',)
    max_num = 0

class ConversationAdmin(admin.ModelAdmin):

    date_hierarchy = 'start_time'
    list_display = ('subject', 'start_time')


    fields = ('start_time', 'subject')

    if not CONVERSATION_EDITABLE:
        readonly_fields = ('start_time', 'subject')

    inlines = [
        ParticipantInline,
        ChatMessageInline,
        ConversationFormEntryInline,
    ]

    def get_changelist(self, request, **kwargs):
        ChangeList = super(ConversationAdmin, self).get_changelist(request, **kwargs)

        class SelectList(ChangeList):
            def __init__(self, *args, **kwargs):
                super(SelectList, self).__init__(*args, **kwargs)
                self.title = _("Conversations")

        return SelectList

    def queryset(self, request):
        all_conversations = super(ConversationAdmin, self).queryset(request)

        own = all_conversations.filter(
          participant__user=request.user,
          participant__role=Participant.ROLE_STAFF,
        )


        if request.user.is_superuser:
            # don't restrict the super user
            return all_conversations

        if request.user.has_perm('common.view_conversations_of_all_branch_offices'):
            # don't restrict the user, can view all conversations
            return all_conversations

        if request.user.has_perm('common.view_conversations_of_own_branch_office'):
            # restrict user to conversations from same branch office

            try:
                users_office = request.user.additionaluserinformation.branch_office
            except AdditionalUserInformation.DoesNotExist:
                # no user metadata is created, thus no branch office, fallback
                # to restrictive behaviour:
                return own

            return all_conversations.filter(
              participant__user__additionaluserinformation__branch_office=users_office,
            )

        # restrict user to own conversations
        return own

admin.site.register(Conversation, ConversationAdmin)
admin.site.disable_action('delete_selected')
