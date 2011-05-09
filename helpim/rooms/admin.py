from helpim.rooms.models import One2OneRoom
from django.contrib import admin

class One2OneRoomAdmin(admin.ModelAdmin):
    model = One2OneRoom
    list_filter = ('status', 'staff')
    list_display = (
      'current_status', 'staff', 'staff_nick', 'client', 'client_nick', 'jid'
    )

admin.site.register(One2OneRoom, One2OneRoomAdmin)
