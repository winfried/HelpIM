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
from helpim.questionnaire.models import ConversationFormEntry, Questionnaire

from helpim.conversations.widgets import IframeEditableWidget, IframeReadonlyWidget

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
        # decide how to render ConversationFormEntry.entry field
        if db_field.name == 'entry':
            request = kwargs.get('request', None)
            
            # users that are 1) assigned to conversation as staff or 2) have can_revise_questionnaire permission see editable Questionnaire
            if not request is None and (request.user == self.current_conversation.getStaff().user or request.user.has_perm('questionnaire.can_revise_questionnaire')):
                kwargs['widget'] = IframeEditableWidget
                return super(admin.StackedInline, self).formfield_for_dbfield(db_field, **kwargs)
            else:
                kwargs['widget'] = IframeReadonlyWidget
                return super(admin.StackedInline, self).formfield_for_dbfield(db_field, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # store Conversation instance about to be displayed in admin
        if not obj is None:
            self.current_conversation = obj
        
        return super(admin.StackedInline, self).get_formset(request, obj, **kwargs)

    model = ConversationFormEntry
    readonly_fields = ('position',)
    can_delete = False
    max_num = 0

class ConversationAdmin(admin.ModelAdmin):

    date_hierarchy = 'start_time'
    list_display = (
      'pk',
      'start_time',
      'duration',
      'client_name',
      'staff_name',
      'subject',
    )
    list_display_links = ('pk', 'start_time', 'subject')

    fields = ('start_time', 'subject')

    if not CONVERSATION_EDITABLE:
        readonly_fields = ('start_time', 'subject')

    inlines = [
        ParticipantInline,
        ChatMessageInline,
        ConversationFormEntryInline,
    ]

    def __init__(self, *args, **kwargs):
        super(ConversationAdmin, self).__init__(*args, **kwargs)

        # show extra column to remind to submit SC Questionnaire
        # there must be a SC Questionnaire defined to display column
        # 
        # seemingly django caches the admin instance, so changing the returned value will probably require a restart
        if Questionnaire.objects.filter(position='SC').count() > 0:
            self.list_display += ('needs_questionnaire',)

    def needs_questionnaire(self, obj):
        '''
        Show a reminder that this Conversation has a Questionnaire at position SC which hasn't been filled out.
        There must be a SC-type Questionnaire defined somewhere for the reminder to occur.
        '''
        is_filled_out = obj.conversationformentry_set.filter(position='SC').count() > 0
        
        if not is_filled_out:
            return _('No')
        else:
            return _('Yes')
    needs_questionnaire.short_description = _('Staff submitted?')

    def get_changelist(self, request, **kwargs):
        ChangeList = super(ConversationAdmin, self).get_changelist(request, **kwargs)

        class SelectList(ChangeList):
            def __init__(self, *args, **kwargs):
                super(SelectList, self).__init__(*args, **kwargs)
                self.title = _("Conversations")

        return SelectList

    def queryset(self, request):
        all_conversations = super(ConversationAdmin, self).queryset(
          request
        ).filter(
          participant__role=Participant.ROLE_CLIENT,
        )

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

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}

        # augment context with SC-type questionnaire, if not yet submitted
        try:
            sc_questionnaire = Questionnaire.objects.filter(position='SC')[0]

            # check if already submitted answer to questionnaire
            if sc_questionnaire.conversationformentry_set.filter(conversation__id=object_id).count() == 0:
                extra_context['staff_questionnaire'] = sc_questionnaire
        except IndexError:
            pass

        return super(ConversationAdmin, self).change_view(request, object_id, extra_context)

admin.site.register(Conversation, ConversationAdmin)
admin.site.disable_action('delete_selected')
