from helpim.rooms.models import One2OneRoom
from django.contrib import admin

class One2OneRoomAdmin(admin.ModelAdmin):
    model = One2OneRoom
    list_display_links = ('jid',)
    list_display = (
      'jid', 'status', 'staff', 'staff_nick', 'client', 'client_nick', 'joinLink'
    )

admin.site.register(One2OneRoom, One2OneRoomAdmin)
