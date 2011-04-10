from helpim.groups.models import Group, Meeting, Member
from django.contrib import admin

class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    readonly_fields = ['access_token']

class MeetingInline(admin.StackedInline):
    model = Meeting
    extra = 0
    fields = ['start_time']

class GroupAdmin(admin.ModelAdmin):
    inlines = [MemberInline, MeetingInline]

admin.site.register(Group, GroupAdmin)
