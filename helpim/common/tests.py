from datetime import datetime
import pickle

from django import template
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase

from helpim.common.management.commands.hi_import_db import Importer, HIData, HIUser
from helpim.common.models import AdditionalUserInformation, BranchOffice
from helpim.common.templatetags.if_app_installed import do_if_app_installed


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

    def test_import_users(self):
        # create User objects with properties to test
        marked_deleted = HIUser(username='del', email='del@del.de', password='sha1$hashash', deleted_at=datetime(2005, 1, 1, 12, 30), branch=None, is_superuser=False, is_coordinator=False, is_careworker=False)
        branchoffice_user1 = HIUser(username='branchuser1', email='branch@branch.com', password='sha1$hashash', deleted_at=None, branch='Amsterdam', is_superuser=True, is_coordinator=False, is_careworker=False)
        branchoffice_user2 = HIUser(username='branchuser2', email='branch@branch.com', password='sha1$hashash', deleted_at=None, branch='Amsterdam', is_superuser=True, is_coordinator=False, is_careworker=False)

        super_user = HIUser(username='superuser', email='super@worker.com', password='sha1$hashash', deleted_at=None, branch=None, is_superuser=True, is_coordinator=False, is_careworker=False)
        coordinator_user = HIUser(username='coordinator', email='coord@worker.com', password='sha1$hashash', deleted_at=None, branch=None, is_superuser=False, is_coordinator=True, is_careworker=False)
        careworker_user = HIUser(username='careworker', email='care@worker.com', password='sha1$hashash', deleted_at=None, branch=None, is_superuser=False, is_coordinator=False, is_careworker=True)

        obj = HIData(users=[
            HIUser(username='adam', email='adam@adam.com', password='sha1$hashash', deleted_at=None, branch=None, is_superuser=True, is_coordinator=False, is_careworker=False),
            HIUser(username="bob", email='bob@bob.com', password='sha1$hashash', deleted_at=None, branch=None, is_superuser=False, is_coordinator=False, is_careworker=False),
            marked_deleted,
            branchoffice_user1,
            branchoffice_user2,
            super_user,
            coordinator_user,
            careworker_user,
        ])

        # check database state pre-import
        self.assertEqual(0, len(User.objects.all()))
        self.assertEqual(0, len(AdditionalUserInformation.objects.all()))
        self.assertEqual(0, len(BranchOffice.objects.all()))

        # import data
        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_users()

        self.assertEqual(7, len(User.objects.all()))
        self.assertEqual('adam@adam.com', User.objects.filter(username__exact='adam')[0].email)
        self.assertEqual(True, User.objects.filter(username__exact='adam')[0].is_superuser)
        self.assertEqual('bob', User.objects.filter(email__exact='bob@bob.com')[0].username)

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
