from django.contrib import admin

from helpim.buddychat.models import BuddyChatProfile

class BuddyChatProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('user', 'activation_key', 'ready', 'volunteer')
            })
        )

    list_display = ('user', 'ready', 'volunteer')
    list_filter = ('ready', 'volunteer')
    list_editable = ('volunteer',)
    readonly_fields = ('user', 'ready', 'activation_key')

admin.site.register(BuddyChatProfile, BuddyChatProfileAdmin)
