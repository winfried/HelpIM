from groups.models import Group, Meeting, Member
from django.contrib import admin

class MemberInline(admin.TabularInline):
    date_hierarchy = 'created_at'
    model = Member
    extra = 0

class MeetingInline(admin.TabularInline):
    model = Meeting
    extra = 0

class GroupAdmin(admin.ModelAdmin):
    inlines = [MemberInline, MeetingInline]

admin.site.register(Group, GroupAdmin)
admin.site.register(Member)
admin.site.register(Meeting)
