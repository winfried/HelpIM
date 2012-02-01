from datetime import datetime, timedelta
import sys

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from registration.models import RegistrationProfile

from helpim.buddychat.models import BuddyChatProfile, QuestionnaireFormEntry
from helpim.questionnaire.models import Questionnaire


class MockDatetime(datetime):
    '''
    mocks now() of datetime.datetime, such that a value can be set
    that will be returned on subsequent calls to now()
    '''

    @classmethod
    def set_now(cls, n):
        cls.n = n

    @classmethod
    def now(cls):
        if cls.n:
            return cls.n
        else:
            raise Exception('must set datetime before using set_now()')


class BuddyChatProfileTestCase(TestCase):
    def setUp(self):
        super(BuddyChatProfileTestCase, self).setUp()

        self.buddy_user = User.objects.create_user('buddyuser', 'user@buddy.com', 'test')
        self.buddy_profile = BuddyChatProfile.objects.create(self.buddy_user, RegistrationProfile.ACTIVATED)

        self.careworker_user = User.objects.create_user('care', 'care@workers.com', 'test')

    def _createQuestionnaireFormEntry(self, created_at, position):
        '''creates a new QuestionnaireFormEntry object with an arbitrary created_at value'''
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
        # use Mock in this module and in buddychat.models to be able to dictate what now() returns
        datetime = MockDatetime
        import helpim.buddychat.models
        helpim.buddychat.models.datetime = MockDatetime

        datetime.set_now(datetime(2000, 1, 1, 0, 0))
        interval = timedelta(**settings.RECURRING_QUESTIONNAIRE_INTERVAL)

        # initially, BuddyChatProfile is not coupled
        # not coupled -> no need to take recurring questionnaire
        self.assertFalse(self.buddy_profile.is_coupled())
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # couple buddy with careworker
        self.buddy_profile.careworker = self.careworker_user
        self.buddy_profile.coupled_at = datetime.now()
        self.buddy_profile.save()

        # no recurring questionnaire configured -> yields None
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # configure such recurring Questionnaires
        # buddy was coupled just now, too early to require recurring (one interval has to pass)
        qCX, created = Questionnaire.objects.get_or_create(position='CX')
        qSX, created = Questionnaire.objects.get_or_create(position='SX')
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # first CX/SX request after 1 RECURRING_QUESTIONNAIRE_INTERVAL has passed, issue to both roles
        datetime.set_now(self.buddy_profile.coupled_at + 1 * interval)
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('CX'), qCX)
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('SX'), qSX)

        # careseeker answers right away, doesnt get request anymore
        self._createQuestionnaireFormEntry(datetime.now(), 'CX')
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('CX'))

        # careworker is slower, answers after half the interval has passed (chosen randomly)
        datetime.set_now(self.buddy_profile.coupled_at + 1 * interval + interval / 2)
        self._createQuestionnaireFormEntry(datetime.now(), 'SX')
        self.assertIsNone(self.buddy_profile.needs_questionnaire_recurring('SX'))

        # despite different reaction times, both roles get the next Questionnaire request at the exact same time
        datetime.set_now(self.buddy_profile.coupled_at + 2 * interval)
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('CX'), qCX)
        self.assertEquals(self.buddy_profile.needs_questionnaire_recurring('SX'), qSX)

        # restore original datetime object
        datetime = sys.modules['datetime'].datetime
        helpim.buddychat.models.datetime = datetime

class QuestionnaireFormEntryManagerTest(TestCase):
    def setUp(self):
        super(QuestionnaireFormEntryManagerTest, self).setUp()

        perm_careworker, created = Permission.objects.get_or_create(codename='is_careworker')
        perm_coordinator, created = Permission.objects.get_or_create(codename='is_coordinator')

        # create User accounts
        self.buddy_user = User.objects.create_user('buddyuser', 'user@buddy.com', 'test')
        self.other_user = User.objects.create_user('other', 'other@buddy.com', 'test')
        self.careworker_user = User.objects.create_user('care', 'care@workers.com', 'test')
        self.careworker_user.user_permissions.add(perm_careworker)
        self.coordinator_user = User.objects.create_user('coord', 'coord@workers.com', 'test')
        self.coordinator_user.user_permissions.add(perm_coordinator)

        # create profiles        
        self.buddy_profile = BuddyChatProfile.objects.create(self.buddy_user, RegistrationProfile.ACTIVATED)
        self.buddy_profile.careworker = self.careworker_user
        self.buddy_profile.save()
        self.other_profile = BuddyChatProfile.objects.create(self.other_user, RegistrationProfile.ACTIVATED)

        # create a QuestionnaireFormEntry of each type and profile
        for pos in ['CR', 'CA', 'CX', 'SX']:
            for profile in [self.buddy_profile, self.other_profile]:
                q, created = Questionnaire.objects.get_or_create(position=pos)
                QuestionnaireFormEntry.objects.create(position=pos, buddychat_profile=profile, questionnaire=q)

    def test_for_profile_and_user(self):
        # legal accesses
        # careseeker -> own profile
        result = QuestionnaireFormEntry.objects.for_profile_and_user(self.buddy_profile, self.buddy_user)
        self.assertEqual(len(result), 3)
        self.assertListEqual(['CR', 'CA', 'CX'], [qfe.position for qfe in result])
        self.assertListEqual([self.buddy_profile, self.buddy_profile, self.buddy_profile], [qfe.buddychat_profile for qfe in result])

        # careworker -> profile he is assigned to
        result = QuestionnaireFormEntry.objects.for_profile_and_user(self.buddy_profile, self.careworker_user)
        self.assertEqual(len(result), 1)
        self.assertListEqual(['SX'], [qfe.position for qfe in result])
        self.assertListEqual([self.buddy_profile], [qfe.buddychat_profile for qfe in result])

        # coordinator
        result = QuestionnaireFormEntry.objects.for_profile_and_user(self.buddy_profile, self.coordinator_user)
        self.assertEquals(len(result), 4)
        self.assertListEqual(['CR', 'CA', 'CX', 'SX'], [qfe.position for qfe in result])
        self.assertListEqual([self.buddy_profile, self.buddy_profile, self.buddy_profile, self.buddy_profile], [qfe.buddychat_profile for qfe in result])


        # illegal accesses
        # careseeker -> foreign profile
        result = QuestionnaireFormEntry.objects.for_profile_and_user(self.other_profile, self.buddy_user)
        self.assertEqual(len(result), 0)

        # careworker -> profile he is not assigned to
        result = QuestionnaireFormEntry.objects.for_profile_and_user(self.other_profile, self.careworker_user)
        self.assertEqual(len(result), 0)

        # coordinator
        result = QuestionnaireFormEntry.objects.for_profile_and_user(self.other_profile, self.coordinator_user)
        self.assertEquals(len(result), 4)
        self.assertListEqual(['CR', 'CA', 'CX', 'SX'], [qfe.position for qfe in result])
        self.assertListEqual([self.other_profile, self.other_profile, self.other_profile, self.other_profile], [qfe.buddychat_profile for qfe in result])
