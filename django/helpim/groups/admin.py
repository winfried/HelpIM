from groups.models import Group, Meeting, Member, MeetingParticipant
from django.contrib import admin

admin.site.register(Group)
admin.site.register(Member)
admin.site.register(Meeting)
admin.site.register(MeetingParticipant)
