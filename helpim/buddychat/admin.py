from django.contrib import admin

from helpim.buddychat.models import BuddyChatProfile

class BuddyChatProfileAdmin(admin.ModelAdmin):
    pass

admin.site.register(BuddyChatProfile)
