from django.contrib import admin

from helpim.buddychat.models import BuddyChatProfile

class BuddyChatProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'ready', 'volunteer')
    list_filter = ('ready', 'volunteer')
    list_editable = ('volunteer',)

admin.site.register(BuddyChatProfile, BuddyChatProfileAdmin)
