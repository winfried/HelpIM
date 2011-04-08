from conversations.models import Conversation, Participant
from django.contrib import admin

class ConversationAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_time'
    list_display = ('subject', 'start_time')


    fields = ('start_time', 'subject')
    readonly_fields = ('start_time', 'subject')

admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Participant)
admin.site.disable_action('delete_selected')
