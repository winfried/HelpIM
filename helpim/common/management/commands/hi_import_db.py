from collections import namedtuple
import os.path
import pickle

from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand

from forms_builder.forms.models import Field
from forms_builder.forms.fields import *

from helpim.common.models import AdditionalUserInformation, BranchOffice
from helpim.conversations.models import Chat, Conversation, Participant
from helpim.questionnaire.models import Questionnaire


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
            imp.import_chats()

class Importer():
    def __init__(self):
        # these dictionaries are used to convert primary key ids between the systems,
        # since they will change during conversion
        self.chat_ids = {}

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

    def import_chats(self):
        for c in self.data.chats:
            new_chat = Chat(start_time=c.started_at, subject=c.subject)
            new_chat.save()
            self.chat_ids[c.id] = new_chat.id

            if not c.staff_name is None:
                try:
                    staff_user = User.objects.filter(username__exact=c.staff_name)[0]
                except:
                    print "Couldnt find associated User with username: %s" % c.staff_name
                    staff_user = None

                staff = Participant(conversation=new_chat, name=c.staff_name, user=staff_user, role=Participant.ROLE_STAFF, ip_hash=c.staff_ip)
                staff.save()

            if not c.client_name is None:
                client = Participant(conversation=new_chat, name=c.client_name, user=None, role=Participant.ROLE_CLIENT, ip_hash=c.client_ip, blocked=c.client_blocked, blocked_at=c.client_blocked_at)
                client.save(keep_blocked_at=True)

    def import_questionnaires(self):
        for q in self.data.questionnaires:
            new_questionnaire = Questionnaire(title=q.title, position=q.position, intro=q.intro, response=q.response)
            new_questionnaire.save()

            for field in q.fields:
                new_field = Field(form=new_questionnaire, label=field.label, field_type=self._convert_field_type(field.type), choices=field.choices or '', visible=field.visible is False)
                new_field.save()

    def _convert_field_type(self, id22):
        '''takes a field-type-id from HelpIM 2.2, returns the corresponding field-type in 3.1'''

        # field-type in 2.2 -> field-type in 3.1
        lookup = {
            1: TEXT,
            2: TEXTAREA,
            3: EMAIL,
            4: CHECKBOX,
            5: CHECKBOX_MULTIPLE,
            6: SELECT,
            7: SELECT_MULTIPLE,
            8: RADIO_MULTIPLE,
            9: FILE,
            10: DATE,
            11: DATE_TIME,
            12: HIDDEN,
            13: NUMBER,
            14: URL,
            14: 100, # ScaleField
            15: 101, # DoubleDrop
        }

        return lookup[id22]

    def _get_chat_id(self, id22):
        '''takes the id of a Chat object in the 2.2 database, returns the id of the converted Chat object in the 3.1 database'''
        return self.chat_ids[id22]


HIData = namedtuple('HIData', ['users', 'chats', 'questionnaires'])
HIUser = namedtuple('HIUser', ['username', 'first_name', 'last_name', 'email', 'password', 'deleted_at', 'branch', 'is_superuser', 'is_coordinator', 'is_careworker'])
HIChat = namedtuple('HIChat', [
    'id', # identifier of this chat in 2.2
    'started_at',
    'subject',
    'client_name',
    'client_ip',
    'client_blocked',
    'client_blocked_at',
    'staff_name',
    'staff_user', # references a User by `username`
    'staff_ip',
])
HIQuestionnaire = namedtuple('HIQuestionnaire', [
    'id',
    'title',
    'position',
    'intro',
    'response',
    'fields', # a list of HIQuestionnaireField
])
HIQuestionnaireField = namedtuple('HIQuestionnaireField', [
    'label',
    'type',
    'choices',
    'visible',
])
