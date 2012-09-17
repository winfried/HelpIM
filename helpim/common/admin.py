import sys

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from helpim.common.models import AdditionalUserInformation, AdministrativeUser, BranchOffice, BranchUser, EventLog


class AdditionalUserInformationInline(admin.StackedInline):
    model = AdditionalUserInformation

class AdditionalUserInformationAdmin(UserAdmin):
    inlines = [AdditionalUserInformationInline]

class AdditionalUserInformationAdministrativeUserInline(admin.StackedInline):
    """
    to be used by BranchUserAdmin
    """
    model = AdditionalUserInformation
    can_delete = False

class AdministrativeUserAdmin(AdditionalUserInformationAdmin):
    """
    Restricted view on Users:
      * add/change/delete non-super users
      * no password hash field, only a link to the change password form
      * no staff-status checkbox (always on)
      * no super-user status checkbox (always off)
      * no box for user-level permissions
      * new AdministrativeUsers: default group 'careworkers' (when present)
    """

    inlines = [AdditionalUserInformationAdministrativeUserInline]

    list_display = ('username', 'email', 'first_name', 'last_name',)
    list_filter = ()

    fieldsets = (
        (None, {'fields': ('username', 'password_change')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Groups'), {'fields': ('groups',)}),
    )

    readonly_fields = ('password_change', 'last_login', 'date_joined',)

    def queryset(self, request):
        # exclude django superusers
        qs = super(AdditionalUserInformationAdmin, self).queryset(request)
        qs = qs.exclude(is_superuser=True)
        return qs

    def formfield_for_manytomany(self, db_field, request=None, extra_groups_exclude=[], **kwargs):
        # restrict choices for groups to groups which have a number of permissions equal or less to requesting user's group
        # we use this heuristic to establish a power ranking of the groups
        if db_field.name == 'groups':
            try:
                if request.user.is_superuser:
                    own_permission_count = sys.maxsize
                else:
                    # group with highest count of permissions that current user is member of
                    own_permission_count = request.user.groups.annotate(num_permissions=Count('permissions')).order_by('-num_permissions')[0].num_permissions
            except:
                own_permission_count = 0

            kwargs['queryset'] = Group.objects.exclude(name__in=extra_groups_exclude).annotate(num_permissions=Count('permissions')).exclude(num_permissions__gt=own_permission_count)
        return AdditionalUserInformationAdmin.formfield_for_manytomany(self, db_field, request=request, **kwargs)

    def save_model(self, request, obj, form, change):
        """called when inserting or updating"""

        if not change:
            # set default rights
            obj.is_staff = True
            obj.is_superuser = False
            obj.save()

            # add new AdministrativeUsers to group Careworkers by default
            try:
                careworkers = Group.objects.get(name='careworkers')
                obj.groups.add(careworkers)
            except Group.DoesNotExist:
                pass
        else:
            obj.save()

    def password_change(self, obj):
        """only show link to 'change password' form"""
        return mark_safe('Use the <a href=\"password/\">change password form</a>.')
    password_change.short_description = _('Password')

class AdditionalUserInformationBranchUserInline(admin.StackedInline):
    """
    to be used by BranchUserAdmin
    """
    model = AdditionalUserInformation

    fieldsets = (
        (None, {'fields': ('branch_office', 'chat_nick', 'chat_priority')}),
    )

    readonly_fields = ('branch_office',)
    can_delete = False

class BranchUserAdmin(AdministrativeUserAdmin):
    """
    In addition to the restrictions imposed by AdministrativeUser:
      * add/modify/delete users in own branch office only
      * no box for branche office, default is the own branch office
      * not possible to make somebody member of the group 'admins'
    """

    inlines = [AdditionalUserInformationBranchUserInline]

    def queryset(self, request):
        # filter out users from other branchoffices
        try:
            users_office = request.user.additionaluserinformation.branch_office
            qs = super(AdditionalUserInformationAdmin, self).queryset(request)
            qs = qs.filter(additionaluserinformation__branch_office=users_office)
            return qs
        except AdditionalUserInformation.DoesNotExist:
            # no user metadata is created, thus no branch office
            # show nothing
            return User.objects.none()

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'groups':
            # same as base class, but never allow to assign group 'admins'
            kwargs['extra_groups_exclude'] = ['admins']

        return AdministrativeUserAdmin.formfield_for_manytomany(self, db_field, request=request, **kwargs)

    def save_formset(self, request, form, formset, change):
        """called when inlines are inserted or updated"""

        # add new BranchUser to same BranchOffice as current User
        if not change:
            try:
                users_office = request.user.additionaluserinformation.branch_office
                obj = User.objects.get(username=form.cleaned_data['username'])

                profile, created = AdditionalUserInformation.objects.get_or_create(user=obj)
                profile.branch_office = users_office
                profile.chat_nick = formset.cleaned_data[0]['chat_nick']
                profile.chat_priority = formset.cleaned_data[0]['chat_priority']
                profile.save()
            except AdditionalUserInformation.DoesNotExist:
                pass
        else:
            AdministrativeUserAdmin.save_formset(self, request, form, formset, change)

admin.site.unregister(User)
admin.site.register(User, AdditionalUserInformationAdmin)
admin.site.register(BranchUser, BranchUserAdmin)
admin.site.register(AdministrativeUser, AdministrativeUserAdmin)
admin.site.register(BranchOffice)
admin.site.register(EventLog)
