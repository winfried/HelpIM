from datetime import datetime
import pickle

from django import template
from django.conf import settings
from django.contrib.auth.models import User
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase

from helpim.common.management.commands.hi_import_db import Importer, HIData, HIUser
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

        self.importer = Importer()

    def test_import_users(self):
        marked_deleted = HIUser(username='del', email='del@del.de', password='sha1$hashash', deleted_at=datetime(2005, 1, 1, 12, 30), is_staff=False)
        
        obj = HIData(users=[
            HIUser(username='adam', email='adam@adam.com', password='sha1$hashash', deleted_at=None, is_staff=True),
            HIUser(username="bob", email='bob@bob.com', password='sha1$hashash', deleted_at=None, is_staff=False),
            marked_deleted
        ])

        self.assertEqual(0, len(User.objects.all()))

        self.importer.from_string(pickle.dumps(obj))
        self.importer.import_users()

        self.assertEqual(2, len(User.objects.all()))
        self.assertEqual('adam@adam.com', User.objects.filter(username__exact='adam')[0].email)
        self.assertEqual(True, User.objects.filter(username__exact='adam')[0].is_staff)
        self.assertEqual('bob', User.objects.filter(email__exact='bob@bob.com')[0].username)
        
        self.assertEqual(0, User.objects.filter(username__exact=marked_deleted.username).count())
