from conversations.models import Conversation, Participant
from django.contrib import admin

class ConversationAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_time'

admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Participant)
