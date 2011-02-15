from groups.models import Group, Meeting, Member, MeetingParticipant
from django.contrib import admin

class MemberInline(admin.TabularInline):
    model = Member
    extra = 0

class GroupAdmin(admin.ModelAdmin):
    inlines = [MemberInline]

admin.site.register(Group, GroupAdmin)
admin.site.register(Member)
admin.site.register(Meeting)
admin.site.register(MeetingParticipant)
