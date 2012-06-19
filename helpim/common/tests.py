from datetime import datetime, timedelta
import pickle

from django import template
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase

from forms_builder.forms.models import Field, FieldEntry, Form, FormEntry
from forms_builder.forms.fields import *

from helpim.common.management.commands.hi_import_db import Importer, HIChat, HIData, HIMessage, HIQuestionnaire, HIQuestionnaireAnswer, HIQuestionnaireField, HIUser
from helpim.common.models import AdditionalUserInformation, BranchOffice
from helpim.common.templatetags.if_app_installed import do_if_app_installed
from helpim.conversations.models import Chat, ChatMessage, Participant
from helpim.questionnaire.models import ConversationFormEntry, Questionnaire


class TemplateTagsTestCase(TestCase):
    def setUp(self):
        super(TemplateTagsTestCase, self).setUp()

        register = template.Library()
        register.tag(name='ifappinstalled', compile_function=do_if_app_installed)
        template.libraries['if_app_installed'] = register

    def test_if_app_installed(self):
        # overwrite apps that are installed
        old_ia = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = ['django.admin', 'mycompany.firstapp', 'foreign.app']

        # test for app installed
        out = Template("{% load if_app_installed %}"
            "{% ifappinstalled mycompany.firstapp %}"
            "    {{ hello }}"
            "{% endifappinstalled %}"
        ).render(Context({ 'hello': 'the first app is installed'}))
        self.assertEqual(out.strip(), 'the first app is installed')

        # test for app not installed
        out = Template("{% load if_app_installed %}"
            "{% ifappinstalled app.neverinstalled %}"
            "    {{ hello }}"
            "{% endifappinstalled %}"
        ).render(Context({ 'hello': 'the first app is installed'}))
        self.assertEqual(out.strip(), '')


        # parameter missing
        render = lambda t: Template(t).render(Context())
        self.assertRaises(TemplateSyntaxError, render,
            "{% load if_app_installed %}"
            "{% ifappinstalled %}"
            "    string"
            "{% endifappinstalled %}"
        )

        # restore settings.INSTALLED_APP
        settings.INSTALLED_APPS = old_ia


class ImporterTestCase(TestCase):
    def setUp(self):
        super(ImporterTestCase, self).setUp()

        perm_careworker, created = Permission.objects.get_or_create(codename='is_careworker')
        perm_coordinator, created = Permission.objects.get_or_create(codename='is_coordinator')

        self.importer = Importer()

    def _updated_copy(self, dict, update):
        '''creates a copy of `dict`, updates its entries using `update` and returns the resulting dict'''

        new_dict = dict.copy()
        new_dict.update(update)
        return new_dict

    def test_import_users(self):
        # create User objects with properties to test
        defaults = { 'first_name': 'ffff4', 'last_name': 'lll3', 'chat_nick': None, 'password': 'notsosecret', 'deleted_at': None, 'branch': None, 'is_superuser': False, 'is_coordinator': False, 'is_careworker': False, }

        normal_user = HIUser(**self._updated_copy(defaults, { 'username':"bob", 'first_name':'bob', 'last_name': 'bobby', 'email': 'bob@bob.com', 'password': 'noonecanknow', }))
        marked_deleted = HIUser(**self._updated_copy(defaults, { 'username': 'del', 'email': 'del@del.de', 'deleted_at': datetime(2005, 1, 1, 12, 30), }))
        branchoffice_user1 = HIUser(**self._updated_copy(defaults, { 'username': 'branchuser1', 'email': 'branch@branch.com', 'branch': 'Amsterdam', 'is_superuser': True, }))
        branchoffice_user2 = HIUser(**self._updated_copy(defaults, { 'username': 'branchuser2', 'email': 'branch@branch.com', 'branch': 'Amsterdam', 'is_superuser': True, }))
        custom_nick = HIUser(**self._updated_copy(defaults, { 'username': 'custom', 'email': 'cus@tom.com', 'chat_nick': 'mycustomnick', 'branch': 'Amsterdam', }))

        super_user = HIUser(**self._updated_copy(defaults, { 'username': 'superuser', 'email': 'super@worker.com', 'is_superuser': True, }))
        coordinator_user = HIUser(**self._updated_copy(defaults, { 'username': 'coordinator', 'email': 'coord@worker.com', 'is_coordinator': True, }))
        careworker_user = HIUser(**self._updated_copy(defaults, { 'username': 'careworker', 'email': 'care@worker.com', 'is_careworker': True, }))

        obj = HIData(
            users=[
                normal_user,
                marked_deleted,
                branchoffice_user1,
                branchoffice_user2,
                custom_nick,
                super_user,
                coordinator_user,
                careworker_user,
            ],
            chats=[],
            questionnaires=[],
        )

        # check database state pre-import
        self.assertEqual(0, len(User.objects.all()))
        self.assertEqual(0, len(AdditionalUserInformation.objects.all()))
        self.assertEqual(0, len(BranchOffice.objects.all()))

        # import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_all()

        self.assertEqual(7, len(User.objects.all()))
        self.assertEqual(normal_user['username'], User.objects.filter(email__exact=normal_user['email'])[0].username)
        self.assertEqual(normal_user['first_name'], User.objects.filter(email__exact=normal_user['email'])[0].first_name)
        self.assertEqual(normal_user['last_name'], User.objects.filter(email__exact=normal_user['email'])[0].last_name)
        self.assertEqual(True, User.objects.filter(username__exact=normal_user['username'])[0].check_password('noonecanknow'))

        # deleted users
        self.assertEqual(0, User.objects.filter(username__exact=marked_deleted['username']).count())

        # division / branchoffice / custom chat nick
        self.assertEqual(3, len(AdditionalUserInformation.objects.all()))
        self.assertEqual(1, len(BranchOffice.objects.all()))

        self.assertEqual('Amsterdam', User.objects.filter(username__exact=branchoffice_user1['username'])[0].additionaluserinformation.branch_office.name)
        self.assertEqual('Amsterdam', User.objects.filter(username__exact=branchoffice_user2['username'])[0].additionaluserinformation.branch_office.name)

        self.assertEqual('mycustomnick', User.objects.filter(username__exact=custom_nick['username'])[0].additionaluserinformation.chat_nick)
        self.assertEqual('Amsterdam', User.objects.filter(username__exact=custom_nick['username'])[0].additionaluserinformation.branch_office.name)

        # permissions
        self.assertEqual(True, User.objects.filter(username__exact=super_user['username'])[0].is_superuser)
        self.assertEqual(True, User.objects.filter(username__exact=super_user['username'])[0].is_staff)

        self.assertEqual(True, User.objects.filter(username__exact=coordinator_user['username'])[0].has_perm('buddychat.is_coordinator'))
        self.assertEqual(True, User.objects.filter(username__exact=coordinator_user['username'])[0].is_staff)

        self.assertEqual(True, User.objects.filter(username__exact=careworker_user['username'])[0].has_perm('buddychat.is_careworker'))
        self.assertEqual(True, User.objects.filter(username__exact=careworker_user['username'])[0].is_staff)

    def test_import_chats(self):
        # create Chat objects with properties to test
        defaults = { 'id': 10, 'started_at': datetime(2012, 1, 3, 15, 0), 'subject': 'Subject', 'messages': [], 'client_name': 'careseeker', 'client_ip': '112233', 'client_blocked': False, 'client_blocked_at': None, 'staff_name': 'bob', 'staff_user': 'bob', 'staff_ip': 'aabbcc', }
        only_staff = HIChat(**self._updated_copy(defaults, {'id': 11, 'subject': 'not-assigned', 'client_name': None, 'client_ip': None, 'client_blocked': None, 'client_blocked_at': None, }))
        blocked_client = HIChat(**self._updated_copy(defaults, {'id': 12, 'subject': 'blocked-client', 'client_ip': 'xxyyzz', 'client_blocked': True, 'client_blocked_at': datetime(2000, 2, 2, 1, 1, 1), }))
        with_messages = HIChat(**self._updated_copy(defaults, { 'id': 13, 'subject': 'talkative', 'messages': [
            HIMessage(event='message', created_at=datetime(2000, 1, 1, 20), who='CLIENT', body='cccc'),
            HIMessage(event='message', created_at=datetime(2000, 1, 1, 21), who='STAFF', body='ssss'),
        ]}))

        obj = HIData(
            users=[
                HIUser(username="bob", first_name='bob', last_name='bobby', email='bob@bob.com', chat_nick=None, password='sha1$3cf22$935cf7156930db92a64bc560385a311d9b7c887a', deleted_at=None, branch=None, is_superuser=False, is_coordinator=False, is_careworker=False)
            ],
            chats=[
                HIChat(**defaults),
                only_staff,
                blocked_client,
                with_messages,
            ],
            questionnaires=[],
        )

        # check database state pre-import
        self.assertEqual(0, len(Chat.objects.all()))
        self.assertEqual(0, len(Participant.objects.all()))
        self.assertEqual(0, len(ChatMessage.objects.all()))

        # import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_all()

        self.assertEqual(len(obj['chats']), len(Chat.objects.all()))
        self.assertEqual(7, len(Participant.objects.all()))
        self.assertEqual(2, len(ChatMessage.objects.all()))


        # normal chat
        c1 = Chat.objects.get(subject=defaults['subject'])
        self.assertEqual(datetime(2012, 1, 3, 15, 0), c1.created_at)
        self.assertEqual('Subject', c1.subject)
        self.assertEqual('bob', c1.getStaff().name)
        self.assertEqual('bob', c1.getStaff().user.username)
        self.assertEqual('aabbcc', c1.getStaff().ip_hash)
        self.assertEqual('careseeker', c1.getClient().name)
        self.assertEqual(None, c1.getClient().user)
        self.assertEqual('112233', c1.getClient().ip_hash)
        self.assertEqual(False, c1.getClient().blocked)
        self.assertEqual(None, c1.getClient().blocked_at)
        self.assertEqual(c1.id, self.importer._get_chat_id(10))

        # only_staff
        c2 = Chat.objects.get(subject=only_staff['subject'])
        self.assertEqual(1, c2.participant_set.count())
        self.assertEqual(c2.id, self.importer._get_chat_id(11))

        # blocked client
        c3 = Chat.objects.get(subject=blocked_client['subject'])
        self.assertEqual(2, c3.participant_set.count())
        self.assertEqual('xxyyzz', c3.getClient().ip_hash)
        self.assertEqual(True, c3.getClient().blocked)
        self.assertEqual(datetime(2000, 2, 2, 1, 1, 1), c3.getClient().blocked_at)
        self.assertEqual(c3.id, self.importer._get_chat_id(12))

        # with messages
        c4 = Chat.objects.get(subject=with_messages['subject'])
        self.assertEqual('cccc', c4.messages.all()[0].body)
        self.assertEqual('ssss', c4.messages.all()[1].body)
        self.assertEqual(timedelta(0, 3600), c4.duration())
        self.assertEqual(c4.started_at, c4.created_at)

    def test_import_questionnaires(self):
        # create Questionnaire objects with properties to test
        unanswered_questionnaire = HIQuestionnaire(
            title='questionnaire 1', position='CB', intro='welcome', response='gotcha',
            fields=[
                HIQuestionnaireField(id=20, label='city?', type='text', choices=None, required=True, visible=True), # text
                HIQuestionnaireField(id=21, label='color?', type='multiple', choices='red,blue,green,yellow,pink', required=True, visible=True), # checkbox_multiple
                HIQuestionnaireField(id=22, label='double', type='doubledrop', choices='one(),two(A,B,C),three', required=False, visible=True), # doubledrop
            ],
            submissions=[],
        )

        obj = HIData(
            users=[],
            chats=[],
            questionnaires=[
                unanswered_questionnaire,
            ],
        )

        # check database state pre-import
        self.assertEqual(0, len(Questionnaire.objects.all()))
        self.assertEqual(0, len(Form.objects.all()))
        self.assertEqual(0, len(Field.objects.all()))

        # import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_all()

        self.assertEqual(len(obj['questionnaires']), len(Questionnaire.objects.all()))
        self.assertEqual(len(obj['questionnaires']), len(Form.objects.all()))
        self.assertEqual(3, len(Field.objects.all()))

        # unanswered questionnaire
        q1 = Questionnaire.objects.filter(title__exact=unanswered_questionnaire['title'])[0]
        self.assertEqual('questionnaire 1', q1.title)
        self.assertEqual('questionnaire-1', q1.slug)
        self.assertEqual(3, q1.fields.count())
        self.assertEqual(TEXT, q1.fields.get(label='city?').field_type)
        self.assertEqual(True, q1.fields.get(label='city?').required)
        self.assertEqual(True, q1.fields.get(label='city?').visible)
        self.assertEqual(q1.fields.get(label='city?').id, self.importer._get_questionnaire_field_id(20))
        self.assertEqual(CHECKBOX_MULTIPLE, q1.fields.get(label='color?').field_type)
        self.assertEqual(101, q1.fields.get(label='double').field_type)
        self.assertEqual(False, q1.fields.get(label='double').required)
        self.assertEqual(q1.fields.get(label='double').id, self.importer._get_questionnaire_field_id(22))

    def test_import_answers(self):
        answered_questionnaire = HIQuestionnaire(
            title='questionnaire 1', position='CB', intro='welcome', response='gotcha',
            fields=[
                HIQuestionnaireField(id=20, label='city?', type='text', choices=None, required=True, visible=True), # text
                HIQuestionnaireField(id=21, label='color?', type='multiple', choices='red,blue,green,yellow,pink', required=True, visible=True), # checkbox_multiple
                HIQuestionnaireField(id=22, label='double', type='doubledrop', choices='one(),two(A,B,C),three', required=False, visible=True), # doubledrop
            ],
            submissions=[
                [ HIQuestionnaireAnswer(field_id=20, entry_time=datetime(2012, 5, 5), value='budapest', conversation_id=10), HIQuestionnaireAnswer(field_id=21, entry_time=datetime(2012, 5, 5), value='3', conversation_id=10), HIQuestionnaireAnswer(field_id=22, entry_time=datetime(2012, 5, 5), value='two>>>B', conversation_id=10) ],
            ],
        )

        obj = HIData(
            users=[
                HIUser(username="bob", first_name='bob', last_name='bobby', email='bob@bob.com', chat_nick=None, password='sha1$3cf22$935cf7156930db92a64bc560385a311d9b7c887a', deleted_at=None, branch=None, is_superuser=False, is_coordinator=False, is_careworker=False)
            ],
            chats=[
                HIChat(id=10, started_at=datetime(2012, 1, 3, 15, 0), subject='Subject', messages=[], client_name='careseeker', client_ip='112233', client_blocked=False, client_blocked_at=None, staff_name='bob', staff_user='bob', staff_ip='aabbcc')
            ],
            questionnaires=[
                answered_questionnaire,
            ],
        )

        # check database state pre-import
        self.assertEqual(0, len(FieldEntry.objects.all()))
        self.assertEqual(0, len(FormEntry.objects.all()))
        self.assertEqual(0, len(ConversationFormEntry.objects.all()))

        # import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_all()

        self.assertEqual(3, len(FieldEntry.objects.all()))
        self.assertEqual(1, len(FormEntry.objects.all()))
        self.assertEqual(1, len(ConversationFormEntry.objects.all()))

        # conversation -> form
        c1 = Chat.objects.get(subject='Subject')
        self.assertEqual(1, c1.conversationformentry_set.count())
        self.assertEqual(datetime(2012, 5, 5), c1.conversationformentry_set.all()[0].created_at)

        # form -> answer
        form_entry = c1.conversationformentry_set.all()[0].entry
        self.assertIsNotNone(form_entry)
        self.assertEqual(answered_questionnaire['title'], form_entry.form.title)
        self.assertEqual(datetime(2012, 5, 5), form_entry.entry_time)
        self.assertEqual(3, form_entry.fields.count())

        # answer -> fields
        self.assertEqual(form_entry, FieldEntry.objects.get(value='budapest').entry)
        self.assertEqual(Field.objects.get(label='city?').id, FieldEntry.objects.get(value='budapest').field_id)
        self.assertEqual(form_entry, FieldEntry.objects.get(value='3').entry)
        self.assertEqual(Field.objects.get(label='color?').id, FieldEntry.objects.get(value='3').field_id)
        self.assertEqual(form_entry, FieldEntry.objects.get(value='two>>>B').entry)
        self.assertEqual(Field.objects.get(label='double').id, FieldEntry.objects.get(value='two>>>B').field_id)
