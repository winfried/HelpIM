from datetime import datetime
import pickle

from django import template
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase

from forms_builder.forms.models import Field, Form
from forms_builder.forms.fields import *

from helpim.common.management.commands.hi_import_db import Importer, HIChat, HIData, HIQuestionnaire, HIQuestionnaireField, HIUser
from helpim.common.models import AdditionalUserInformation, BranchOffice
from helpim.common.templatetags.if_app_installed import do_if_app_installed
from helpim.conversations.models import Chat, Participant
from helpim.questionnaire.models import Questionnaire


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
        defaults = { 'first_name': 'ffff4', 'last_name': 'lll3', 'password': 'sha1$hashash', 'deleted_at': None, 'branch': None, 'is_superuser': False, 'is_coordinator': False, 'is_careworker': False, }

        normal_user = HIUser(**self._updated_copy(defaults, { 'username':"bob", 'first_name':'bob', 'last_name': 'bobby', 'email': 'bob@bob.com', 'password': 'sha1$3cf22$935cf7156930db92a64bc560385a311d9b7c887a', }))
        marked_deleted = HIUser(**self._updated_copy(defaults, { 'username': 'del', 'email': 'del@del.de', 'deleted_at': datetime(2005, 1, 1, 12, 30), }))
        branchoffice_user1 = HIUser(**self._updated_copy(defaults, { 'username': 'branchuser1', 'email': 'branch@branch.com', 'branch': 'Amsterdam', 'is_superuser': True, }))
        branchoffice_user2 = HIUser(**self._updated_copy(defaults, { 'username': 'branchuser2', 'email': 'branch@branch.com', 'branch': 'Amsterdam', 'is_superuser': True, }))

        super_user = HIUser(**self._updated_copy(defaults, { 'username': 'superuser', 'email': 'super@worker.com', 'is_superuser': True, }))
        coordinator_user = HIUser(**self._updated_copy(defaults, { 'username': 'coordinator', 'email': 'coord@worker.com', 'is_coordinator': True, }))
        careworker_user = HIUser(**self._updated_copy(defaults, { 'username': 'careworker', 'email': 'care@worker.com', 'is_careworker': True, }))

        obj = HIData(
            users=[
                normal_user,
                marked_deleted,
                branchoffice_user1,
                branchoffice_user2,
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
        self.importer.import_users()

        self.assertEqual(6, len(User.objects.all()))
        self.assertEqual(normal_user.username, User.objects.filter(email__exact=normal_user.email)[0].username)
        self.assertEqual(normal_user.first_name, User.objects.filter(email__exact=normal_user.email)[0].first_name)
        self.assertEqual(normal_user.last_name, User.objects.filter(email__exact=normal_user.email)[0].last_name)
        self.assertEqual(True, User.objects.filter(username__exact=normal_user.username)[0].check_password('secret'))

        # deleted users
        self.assertEqual(0, User.objects.filter(username__exact=marked_deleted.username).count())

        # division / branchoffice
        self.assertEqual('Amsterdam', User.objects.filter(username__exact=branchoffice_user1.username)[0].additionaluserinformation.branch_office.name)
        self.assertEqual('Amsterdam', User.objects.filter(username__exact=branchoffice_user2.username)[0].additionaluserinformation.branch_office.name)
        self.assertEqual(2, len(AdditionalUserInformation.objects.all()))
        self.assertEqual(1, len(BranchOffice.objects.all()))

        # permissions
        self.assertEqual(True, User.objects.filter(username__exact=super_user.username)[0].is_superuser)
        self.assertEqual(True, User.objects.filter(username__exact=super_user.username)[0].is_staff)

        self.assertEqual(True, User.objects.filter(username__exact=coordinator_user.username)[0].has_perm('buddychat.is_coordinator'))
        self.assertEqual(True, User.objects.filter(username__exact=coordinator_user.username)[0].is_staff)

        self.assertEqual(True, User.objects.filter(username__exact=careworker_user.username)[0].has_perm('buddychat.is_careworker'))
        self.assertEqual(True, User.objects.filter(username__exact=careworker_user.username)[0].is_staff)

    def test_import_chats(self):
        # create Chat objects with properties to test
        defaults = { 'started_at': datetime(2012, 1, 3, 15, 0), 'subject': 'Subject', 'client_name': 'careseeker', 'client_ip': '112233', 'client_blocked': False, 'client_blocked_at': None, 'staff_name': 'bob', 'staff_user': 'bob', 'staff_ip': 'aabbcc', }
        only_staff = HIChat(**self._updated_copy(defaults, {'subject': 'not-assigned', 'client_name': None, 'client_ip': None, 'client_blocked': None, 'client_blocked_at': None, }))
        blocked_client = HIChat(**self._updated_copy(defaults, {'subject': 'blocked-client', 'client_ip': 'xxyyzz', 'client_blocked': True, 'client_blocked_at': datetime(2000, 2, 2, 1, 1, 1), }))

        obj = HIData(
            users=[
                HIUser(username="bob", first_name='bob', last_name='bobby', email='bob@bob.com', password='sha1$3cf22$935cf7156930db92a64bc560385a311d9b7c887a', deleted_at=None, branch=None, is_superuser=False, is_coordinator=False, is_careworker=False)
            ],
            chats=[
                HIChat(**defaults),
                only_staff,
                blocked_client,
            ],
            questionnaires=[],
        )

        # check database state pre-import
        self.assertEqual(0, len(Chat.objects.all()))
        self.assertEqual(0, len(Participant.objects.all()))

        # import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_users()
        self.importer.import_chats()

        self.assertEqual(len(obj.chats), len(Chat.objects.all()))
        self.assertEqual(5, len(Participant.objects.all()))

        # normal chat
        self.assertEqual(datetime(2012, 1, 3, 15, 0), Chat.objects.get(pk=1).start_time)
        self.assertEqual('Subject', Chat.objects.get(pk=1).subject)
        self.assertEqual('bob', Chat.objects.get(pk=1).getStaff().name)
        self.assertEqual('bob', Chat.objects.get(pk=1).getStaff().user.username)
        self.assertEqual('aabbcc', Chat.objects.get(pk=1).getStaff().ip_hash)
        self.assertEqual('careseeker', Chat.objects.get(pk=1).getClient().name)
        self.assertEqual(None, Chat.objects.get(pk=1).getClient().user)
        self.assertEqual('112233', Chat.objects.get(pk=1).getClient().ip_hash)
        self.assertEqual(False, Chat.objects.get(pk=1).getClient().blocked)
        self.assertEqual(None, Chat.objects.get(pk=1).getClient().blocked_at)

        # only_staff
        self.assertEqual(1, Chat.objects.filter(subject__exact=only_staff.subject)[0].participant_set.count())

        # blocked client
        self.assertEqual(2, Chat.objects.filter(subject__exact=blocked_client.subject)[0].participant_set.count())
        self.assertEqual('xxyyzz', Chat.objects.filter(subject__exact=blocked_client.subject)[0].getClient().ip_hash)
        self.assertEqual(True, Chat.objects.filter(subject__exact=blocked_client.subject)[0].getClient().blocked)
        self.assertEqual(datetime(2000, 2, 2, 1, 1, 1), Chat.objects.filter(subject__exact=blocked_client.subject)[0].getClient().blocked_at)

    def test_import_questionnaires(self):
        # create Questionnaire objects with properties to test
        normal_questionnaire = HIQuestionnaire(
            id=55, title='questionnaire 1', position='CB', intro='welcome', response='gotcha',
            fields=[
                HIQuestionnaireField(label='city?', type=1, choices=None, visible=True), # text
                HIQuestionnaireField(label='color?', type=5, choices='red,blue,green,yellow,pink', visible=True), # checkbox_multiple
                HIQuestionnaireField(label='double', type=15, choices='one(),two(A,B,C),three', visible=True), # doubledrop
            ]
        )

        obj = HIData(
            users=[],
            chats=[],
            questionnaires=[
                normal_questionnaire,
            ],
        )

        #check database state pre-import
        self.assertEqual(0, len(Questionnaire.objects.all()))
        self.assertEqual(0, len(Form.objects.all()))
        self.assertEqual(0, len(Field.objects.all()))

        #import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_questionnaires()

        self.assertEqual(len(obj.questionnaires), len(Questionnaire.objects.all()))
        self.assertEqual(len(obj.questionnaires), len(Form.objects.all()))
        self.assertEqual(3, len(Field.objects.all()))

        # normal questionnaire
        q1 = Questionnaire.objects.filter(title__exact=normal_questionnaire.title)[0]
        self.assertEqual('questionnaire 1', q1.title)
        self.assertEqual('questionnaire-1', q1.slug)
        self.assertEqual(3, q1.fields.count())
        self.assertEqual(TEXT, q1.fields.get(label='city?').field_type)
        self.assertEqual(CHECKBOX_MULTIPLE, q1.fields.get(label='color?').field_type)
        self.assertEqual(101, q1.fields.get(label='double').field_type)
