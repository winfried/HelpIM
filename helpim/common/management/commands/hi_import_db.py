from collections import namedtuple
import os.path
import pickle

from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand

from helpim.common.models import AdditionalUserInformation, BranchOffice


class Command(BaseCommand):
    help = 'Imports data from HelpIM 2.2'
    args = 'pickled_datafile [pickled_datafile ...]'

    def handle(self, *files, **options):
        for file in files:
            if not os.path.isfile(file):
                print "Could not find file '%s'" % (file)

            imp = Importer()
            imp.from_file(file)

            imp.import_users()

class Importer():
    def from_file(self, f):
        self.data = pickle.load(f)

    def from_string(self, s):
        self.data = pickle.loads(s)

    def get_users(self):
        return self.data.users

    def import_users(self):
        perm_careworker, created = Permission.objects.get_or_create(codename='is_careworker')
        perm_coordinator, created = Permission.objects.get_or_create(codename='is_coordinator')

        for u in self.data.users:
            # skip user if marked as deleted
            if not u.deleted_at is None:
                continue

            # create User, set basic properties
            new_user = User.objects.create_user(u.username, u.email)
            new_user.first_name = u.first_name
            new_user.last_name = u.last_name
            new_user.password = u.password

            # division, branchoffice, additional-user-information
            if not u.branch is None:
                branchoffice, created = BranchOffice.objects.get_or_create(name=u.branch)
                additional_information, created = AdditionalUserInformation.objects.get_or_create(user=new_user, branch_office=branchoffice)

            # permissions
            if u.is_superuser is True:
                new_user.is_superuser = True
                new_user.is_staff = True
            if u.is_coordinator is True:
                new_user.user_permissions.add(perm_coordinator)
                new_user.is_staff = True
            if u.is_careworker is True:
                new_user.user_permissions.add(perm_careworker)
                new_user.is_staff = True

            new_user.save()


HIData = namedtuple('HIData', ['users'])
HIUser = namedtuple('HIUser', ['username', 'first_name', 'last_name', 'email', 'password', 'deleted_at', 'branch', 'is_superuser', 'is_coordinator', 'is_careworker'])
