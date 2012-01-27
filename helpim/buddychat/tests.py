from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from registration.models import RegistrationProfile

from helpim.buddychat.models import BuddyChatProfile, QuestionnaireFormEntry
from helpim.questionnaire.models import Questionnaire


class BuddyChatProfileTestCase(TestCase):
    def setUp(self):
        super(BuddyChatProfileTestCase, self).setUp()

        self.buddy_user = User.objects.create_user('buddyuser', 'user@buddy.com', 'test')
        self.buddy_profile = BuddyChatProfile.objects.create(self.buddy_user, RegistrationProfile.ACTIVATED)

        self.careworker_user = User.objects.create_user('care', 'care@workers.com', 'test')

    def _createQuestionnaireFormEntry(self, created_at, position):
        q, created = Questionnaire.objects.get_or_create(position=position)

        newQFE = QuestionnaireFormEntry.objects.create(created_at=created_at, position=position, buddychat_profile=self.buddy_profile, questionnaire=q)
        newQFE.created_at = created_at
        newQFE.save()

        return newQFE

    def test_get_latest_questionnaire_entry(self):
        self.assertIsNone(self.buddy_profile.get_latest_questionnaire_entry('CR'))

        qfe1 = self._createQuestionnaireFormEntry(datetime(2011, 11, 1, 16, 0), 'CR')
        self.assertEquals(self.buddy_profile.get_latest_questionnaire_entry('CR'), qfe1)

        qfe2 = self._createQuestionnaireFormEntry(datetime(2011, 11, 1, 16, 16), 'CR')
        self.assertEquals(self.buddy_profile.get_latest_questionnaire_entry('CR'), qfe2)

    def test_needs_questionnaire_CR(self):
        # initially, BuddyChatProfile is not marked ready
        self.assertFalse(self.buddy_profile.ready)

        # database has no CR questionnaire -> None
        self.assertIsNone(self.buddy_profile.needs_questionnaire_CR())

        # there is a CR questionnaire the not-ready client needs to take
        qCR, created = Questionnaire.objects.get_or_create(position='CR')
        self.assertEquals(self.buddy_profile.needs_questionnaire_CR(), qCR)

        # after careseeker has taken questionnaire, dont force him to again
        self.buddy_profile.ready = True
        self.buddy_profile.save()
        self.assertIsNone(self.buddy_profile.needs_questionnaire_CR())

    def test_needs_questionnaire_recurring(self):
        # initially, BuddyChatProfile is not coupled
        # not coupled -> no need to take recurring questionnaire
        self.assertFalse(self.buddy_profile.is_coupled())
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # couple buddy
        self.buddy_profile.careworker = self.careworker_user
        self.buddy_profile.coupled_at = datetime.now()
        self.buddy_profile.save()

        # no recurring questionnaire configured, yields None
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # buddy was coupled just now, too early to require recurring
        qCX, created = Questionnaire.objects.get_or_create(position='CX')
        qSX, created = Questionnaire.objects.get_or_create(position='SX')
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # fake time pass, to trigger first CX request
        self.buddy_profile.coupled_at -= timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL)
        self.buddy_profile.save()
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('CX'), qCX)
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('SX'), qSX)

        # after recurring questionnaire is answered, not another request will be issued until enough time has passed
        qfe_client = QuestionnaireFormEntry.objects.create(entry=None, questionnaire=qCX, buddychat_profile=self.buddy_profile, position='CX')
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        qfe_staff = QuestionnaireFormEntry.objects.create(entry=None, questionnaire=qCX, buddychat_profile=self.buddy_profile, position='SX')
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # fake time pass, to trigger next recurring questionnaire request
        qfe_client.created_at -= timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL)
        qfe_client.save()
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('CX'), qCX)
        
        qfe_staff.created_at -= timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL)
        qfe_staff.save()
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('SX'), qSX)
