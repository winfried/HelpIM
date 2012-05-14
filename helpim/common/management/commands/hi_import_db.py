from collections import namedtuple
import os.path
import pickle

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


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
            new_user = User.objects.create_user(u.username, u.email)
            new_user.password = u.password
            new_user.is_staff = u.is_staff is True
            new_user.save()


HIData = namedtuple('HIData', ['users'])
HIUser = namedtuple('HIUser', ['username', 'email', 'password', 'is_staff'])
