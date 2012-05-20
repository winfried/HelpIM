from collections import namedtuple
import os.path
import pickle

from django.contrib.auth.models import User
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
        for u in self.data.users:
            # skip user if marked as deleted
            if not u.deleted_at is None:
                continue

            new_user = User.objects.create_user(u.username, u.email)
            new_user.password = u.password
            new_user.is_staff = u.is_staff is True

            # division, branchoffice, additional-user-information
            if not u.branch is None:
                branchoffice, created = BranchOffice.objects.get_or_create(name=u.branch)
                additional_information, created = AdditionalUserInformation.objects.get_or_create(user=new_user, branch_office=branchoffice)


            new_user.save()


HIData = namedtuple('HIData', ['users'])
HIUser = namedtuple('HIUser', ['username', 'email', 'password', 'deleted_at', 'branch', 'is_staff'])
