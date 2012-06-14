from collections import namedtuple
import os.path
import pickle
import sys

from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand

from forms_builder.forms.models import Field, FieldEntry, FormEntry
from forms_builder.forms.fields import *

from helpim.common.models import AdditionalUserInformation, BranchOffice
from helpim.conversations.models import Chat, ChatMessage, Conversation, Participant
from helpim.questionnaire.models import ConversationFormEntry, Questionnaire


class Command(BaseCommand):
    help = 'Imports data from HelpIM 2.2'
    args = 'pickled_datafile [pickled_datafile ...]'

    def handle(self, *files, **options):
        print 'Database has %d User, %d Chat, %d Questionnaire' % (len(User.objects.all()), len(Chat.objects.all()), len(Questionnaire.objects.all()))

        for file in files:
            if not os.path.isfile(file):
                print "Could not find file '%s'" % (file)

            print 'Unpickling %s' % (file)

            imp = Importer()
            imp.from_file(file)

            print "Loaded %d HIUser, %d HIChat, %d HIQuestionnaire" % (len(imp.data['users']), len(imp.data['chats']), len(imp.data['questionnaires']),)

            imp.import_all()

        print 'Database has %d User, %d Chat, %d Questionnaire' % (len(User.objects.all()), len(Chat.objects.all()), len(Questionnaire.objects.all()))

class Importer():
    def __init__(self):
        self.data = None

        # these dictionaries are used to convert primary key ids between the systems,
        # since they will change during conversion
        self.chat_ids = {}
        self.questionnaire_field_ids = {}

    def from_file(self, f):
        self.data = pickle.load(open(f, 'rb'))

    def from_string(self, s):
        self.data = pickle.loads(s)

    def print_indent(self, msg, indent=4):
        print "%s%s" % (' ' * indent, msg)

    def import_all(self):
        self.import_users()
        self.import_chats()
        self.import_questionnaires()

    def import_users(self):
        perm_careworker, created = Permission.objects.get_or_create(codename='is_careworker')
        perm_coordinator, created = Permission.objects.get_or_create(codename='is_coordinator')

        for u in self.data['users']:
            print '>>  %s' % str(u)

            # skip user if marked as deleted
            if not u['deleted_at'] is None:
                self.print_indent('marked as deleted')
                continue

            # create User, set basic properties
            try:
                new_user = User.objects.create_user(u['username'], u['email'])
            except:
                print "**  Error creating User: %s: %s" % (sys.exc_info()[0], sys.exc_info()[1])
                continue

            new_user.first_name = u['first_name']
            new_user.last_name = u['last_name']
            new_user.set_password(u['password'])

            # division, branchoffice, additional-user-information
            if not u['branch'] is None:
                branchoffice, created = BranchOffice.objects.get_or_create(name=u['branch'])
                additional_information, created = AdditionalUserInformation.objects.get_or_create(user=new_user)
                additional_information.branch_office = branchoffice
                additional_information.save()
                self.print_indent('Additional user info: %s' % (additional_information.branch_office))

            if not u['chat_nick'] is None and len(u['chat_nick']) > 0:
                additional_information, created = AdditionalUserInformation.objects.get_or_create(user=new_user)
                additional_information.chat_nick = u['chat_nick']
                additional_information.save()
                self.print_indent('Additional User Info: %s' % (additional_information.chat_nick))

            # permissions
            if u['is_superuser'] is True:
                new_user.is_superuser = True
                new_user.is_staff = True
            if u['is_coordinator'] is True:
                new_user.user_permissions.add(perm_coordinator)
                new_user.is_staff = True
            if u['is_careworker'] is True:
                new_user.user_permissions.add(perm_careworker)
                new_user.is_staff = True

            new_user.save()
            self.print_indent('User: %s' % (new_user.username))

    def import_chats(self):
        for c in self.data['chats']:
            new_chat = Chat(created_at=c['started_at'], subject=c['subject'])
            new_chat.save()
            self.chat_ids[c['id']] = new_chat.id

            if not c['staff_name'] is None:
                try:
                    staff_user = User.objects.filter(username__exact=c['staff_name'])[0]
                except:
                    print "Couldnt find associated User with username: %s" % c['staff_name']
                    staff_user = None

                staff = Participant(conversation=new_chat, name=c['staff_name'], user=staff_user, role=Participant.ROLE_STAFF, ip_hash=c['staff_ip'])
                staff.save()

            if not c['client_name'] is None:
                client = Participant(conversation=new_chat, name=c['client_name'], user=None, role=Participant.ROLE_CLIENT, ip_hash=c['client_ip'], blocked=c['client_blocked'], blocked_at=c['client_blocked_at'])
                client.save(keep_blocked_at=True)

            for msg in c['messages']:
                if msg['who'] == 'CLIENT':
                    sender = client
                else:
                    sender = staff

                new_msg = ChatMessage(conversation=new_chat, sender=sender, sender_name=sender.name, created_at=msg['created_at'], body=msg['body'], event=msg['event'])
                new_msg.save()

    def import_questionnaires(self):
        for q in self.data['questionnaires']:
            new_questionnaire = Questionnaire(title=q['title'], position=q['position'], intro=q['intro'], response=q['response'])
            new_questionnaire.save()

            for field in q['fields']:
                new_field = Field(form=new_questionnaire, label=field['label'], field_type=self._convert_field_type(field['type']), choices=field['choices'] or '', required=field['required'] is not False, visible=field['visible'] is not False)
                new_field.save()
                self.questionnaire_field_ids[field['id']] = new_field.id

            for submission in q['submissions']:
                new_formentry = FormEntry(form=new_questionnaire)
                new_cfe = ConversationFormEntry(position=q['position'], questionnaire=new_questionnaire)

                for answer in submission:
                    new_formentry.entry_time = answer['entry_time']
                    new_formentry.save()

                    new_fieldentry = FieldEntry(field_id=self._get_questionnaire_field_id(answer['field_id']), value=answer['value'], entry=new_formentry)
                    new_fieldentry.save()

                    if answer['conversation_id']:
                        new_cfe.entry = new_formentry
                        new_cfe.conversation = Conversation.objects.get(pk=self._get_chat_id(answer['conversation_id']))
                        new_cfe.created_at = answer['entry_time']
                        new_cfe.save()


    def _convert_field_type(self, id22):
        '''takes a field-type-id from HelpIM 2.2, returns the corresponding field-type in 3.1'''

        # field-type in 2.2 -> field-type in 3.1
        lookup = {
            'doubledrop': 101,
            'text': TEXT,
            'textfield': TEXTAREA,
            'textfield_long': TEXTAREA,
            'nummeric': NUMBER,
            'droplist': SELECT,
            'single': CHECKBOX,
            'multiple': CHECKBOX_MULTIPLE,
            'hide': CHECKBOX,
        }
        return lookup[id22]

    def _get_chat_id(self, id22):
        '''takes the id of a Chat object in the 2.2 database, returns the id of the converted Chat object in the 3.1 database'''
        return self.chat_ids[id22]

    def _get_questionnaire_field_id(self, id22):
        return self.questionnaire_field_ids[id22]


def HIData(users=[], chats=[], questionnaires=[]):
    return { 'users': users, 'chats': chats, 'questionnaires': questionnaires }
def HIUser(username, first_name, last_name, email, chat_nick, password, deleted_at, branch, is_superuser, is_coordinator, is_careworker):
    return {
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'chat_nick': chat_nick, # can be None
        'password': password,
        'deleted_at': deleted_at,
        'branch': branch,
        'is_superuser': is_superuser,
        'is_coordinator': is_coordinator,
        'is_careworker': is_careworker
    }
def HIChat(id, started_at, subject, messages, client_name, client_ip, client_blocked, client_blocked_at, staff_name, staff_user, staff_ip):
    return {
        'id': id, # identifier of this chat in 2.2
        'started_at': started_at,
        'subject': subject,
        'messages': messages, # list of messages
        'client_name': client_name,
        'client_ip': client_ip,
        'client_blocked': client_blocked,
        'client_blocked_at': client_blocked_at,
        'staff_name': staff_name,
        'staff_user': staff_user, # references a User by `username`
        'staff_ip': staff_ip,
    }
def HIMessage(event, created_at, who, body):
    return {
        'event': event, # 'message' | 'join' | 'rejoin' | 'left' | 'ended'
        'created_at': created_at,
        'who': who, # 'STAFF' or 'CLIENT'
        'body': body,
    }
def HIQuestionnaire(title, position, intro, response, fields, submissions):
    return {
        'title': title,
        'position': position,
        'intro': intro,
        'response': response,
        'fields': fields, # a list of HIQuestionnaireField
        'submissions': submissions, # a list of list of HIQuestionnaireAnswer
    }
def HIQuestionnaireField(id, label, type, choices, required, visible):
    return {
        'id': id, # identifier of this question in 2.2
        'label': label,
        'type': type,
        'choices': choices,
        'required': required,
        'visible': visible,
    }
def HIQuestionnaireAnswer(field_id, entry_time, value, conversation_id):
    return {
        'field_id': field_id,
        'entry_time': entry_time,
        'value': value,
        'conversation_id': conversation_id, # 2.2 identifier of a Chat that this answer is connected to
    }
