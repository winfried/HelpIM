from datetime import datetime

from django.contrib import admin

from helpim.buddychat.models import BuddyChatProfile

class BuddyChatProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('user', 'activation_key', 'ready', 'volunteer', 'coupled_at')
            }),
        )

    list_display = ('user', 'ready', 'volunteer')
    list_filter = ('ready', 'volunteer')
    list_editable = ('volunteer',)
    readonly_fields = ('user', 'ready', 'activation_key', 'coupled_at')

    def save_model(self, request, obj, form, change):
        if change and 'volunteer' in form.changed_data:
            if obj.volunteer is None:
                obj.coupled_at = None
            else:
                obj.coupled_at = datetime.now()
            obj.save()
            
admin.site.register(BuddyChatProfile, BuddyChatProfileAdmin)
