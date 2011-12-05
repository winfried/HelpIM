from datetime import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from helpim.conversations.models import Chat, Participant, ChatMessage
from helpim.questionnaire.models import ConversationFormEntry, Questionnaire

from forms_builder.forms.models import FormEntry


class ChatStatsProviderTestCase(TestCase):
    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'test')
        self.assertTrue(self.c.login(username=self.user.username, password='test'), 'Could not login')


    def testYearsPagination(self):
        Chat.objects.create(start_time=datetime(2008, 11, 1, 16, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 10), subject='Chat')
        Chat.objects.create(start_time=datetime(2013, 11, 1, 17, 0), subject='Chat')


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertEqual(response.context['prevPage']['value'], 2008)
        self.assertEqual(response.context['currentPage']['value'], 2011)
        self.assertEqual(response.context['nextPage']['value'], 2013)
        for year, pageYear in zip([2008, 2011, 2013], response.context['pagingYears']):
            self.assertEqual(pageYear['value'], year)

        response = self.c.get(reverse('stats_overview', args=['chat', 2008]))
        self.assertEqual(response.context['prevPage'], None)
        self.assertEqual(response.context['currentPage']['value'], 2008)
        self.assertEqual(response.context['nextPage']['value'], 2011)

        response = self.c.get(reverse('stats_overview', args=['chat', 2013]))
        self.assertEqual(response.context['prevPage']['value'], 2011)
        self.assertEqual(response.context['currentPage']['value'], 2013)
        self.assertEqual(response.context['nextPage'], None)


    def testHourAggregation(self):
        '''Chats are aggregated by date and hour'''

        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 10), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 59), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 0), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 11, 18, 0), subject='Chat')


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        self.assertEqual(len(response.context['aggregatedStats'].keys()), 4)
        self.assertEqual(response.context['aggregatedStats'].keys(), ['2011-11-01 16', '2011-11-01 17', '2011-11-01 18', '2011-11-11 18'])


    def testTotalUniqueCount(self):
        '''Uniqueness of Chats determined via hashed IP of Participant in Chat'''

        # 1 unique chatter
        c1 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')
        Participant.objects.create(conversation=c1, name='Chatter1', role=Participant.ROLE_CLIENT, ip_hash='aabbccddeeff')
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 30), subject='Chat')
        Participant.objects.create(conversation=c2, name='Chatter1', role=Participant.ROLE_CLIENT, ip_hash='aabbccddeeff')

        # 2 unique chatters
        c3 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        Participant.objects.create(conversation=c3, name='Chatter2', role=Participant.ROLE_CLIENT, ip_hash='vvwwxxyyzz')
        c4 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 10), subject='Chat')
        Participant.objects.create(conversation=c4, name='Chatter3', role=Participant.ROLE_CLIENT, ip_hash='112233445566')

        # Chat without client-Participant, regard in totalCount but not in uniqueIPs
        Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 0), subject='Chat')


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        # unique Chatters
        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [1, 2, 0]):
            self.assertEqual(actual['uniqueIPs'], expected)


    def testQuestionnairesSubmitted(self):
        '''Counts Questionnaires submitted at beginning of Chat'''

        # Chat without questionnaire
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')

        # Chat with questionnaire before chat
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        q1 = Questionnaire.objects.create()
        f1 = FormEntry.objects.create(entry_time=datetime(2011, 11, 1, 16, 59), form=q1)
        ConversationFormEntry.objects.create(entry=f1, questionnaire=q1, conversation=c2, position='CB', created_at=datetime(2011, 11, 1, 16, 59))


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        # questionnaires submitted
        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [0, 1]):
            self.assertEqual(actual['questionnairesSubmitted'], expected)


    def testBlocked(self):
        '''Participant is blocked if Participant.blocked == True'''

        # 1 blocked chatter
        c1 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')
        Participant.objects.create(conversation=c1, name='Chatter1', role=Participant.ROLE_CLIENT, blocked=True)
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 30), subject='Chat')
        Participant.objects.create(conversation=c2, name='Chatter2', role=Participant.ROLE_CLIENT)

        # 2 blocked chatters
        c3 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        Participant.objects.create(conversation=c3, name='Chatter3', role=Participant.ROLE_CLIENT, blocked=True)
        c4 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 10), subject='Chat')
        Participant.objects.create(conversation=c4, name='Chatter4', role=Participant.ROLE_CLIENT, blocked=True)

        # 0 blocked chatters
        c5 = Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 25), subject='Chat')
        Participant.objects.create(conversation=c5, name='Chatter5', role=Participant.ROLE_CLIENT)
        c6 = Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 35), subject='Chat')
        Participant.objects.create(conversation=c6, name='Chatter6', role=Participant.ROLE_CLIENT)


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [1, 2, 0]):
            self.assertEqual(actual['blocked'], expected)


    def testFull(self):
        pass


    def testQueued(self):
        pass


    def testAssigned(self):
        '''Chat is assigned if both, staff and client Participant have joined'''

        # 1 assigned Chat
        c1 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')
        Participant.objects.create(conversation=c1, name='Chatter1', role=Participant.ROLE_CLIENT)
        Participant.objects.create(conversation=c1, name='Staff1', role=Participant.ROLE_STAFF)

        # Chat only has staff
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 10), subject='Chat')
        Participant.objects.create(conversation=c2, name='Staff2', role=Participant.ROLE_STAFF)

        # Chat only has client
        c3 = Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 15), subject='Chat')
        Participant.objects.create(conversation=c3, name='Chatter2', role=Participant.ROLE_CLIENT)


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [1, 0, 0]):
            self.assertEqual(actual['assigned'], expected)


    def testInteraction(self):
        # Chat without messages -> no interaction
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')

        # only client chatted -> no interaction
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        chatter1 = Participant.objects.create(conversation=c2, name='Chatter1', role=Participant.ROLE_CLIENT)
        ChatMessage.objects.create(conversation=c2, sender=chatter1, event='message', created_at=datetime(2011, 11, 1, 17, 1), body='message text')

        # only staff chatted -> no interaction
        c3 = Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 0), subject='Chat')
        staff1 = Participant.objects.create(conversation=c3, name='Staff1', role=Participant.ROLE_STAFF)
        ChatMessage.objects.create(conversation=c3, sender=staff1, event='message', created_at=datetime(2011, 11, 1, 18, 1), body='message text')

        # client and staff chatted -> interaction
        c4 = Chat.objects.create(start_time=datetime(2011, 11, 1, 19, 0), subject='Chat')
        chatter2 = Participant.objects.create(conversation=c4, name='Chatter2', role=Participant.ROLE_CLIENT)
        staff2 = Participant.objects.create(conversation=c4, name='Staff2', role=Participant.ROLE_STAFF)
        ChatMessage.objects.create(conversation=c4, sender=chatter2, event='message', created_at=datetime(2011, 11, 1, 19, 1), body='message text')
        ChatMessage.objects.create(conversation=c4, sender=staff2, event='message', created_at=datetime(2011, 11, 1, 19, 2), body='message text')


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [0, 0, 0, 1]):
            self.assertEqual(actual['interaction'], expected)


    def testWaitingTime(self):
        pass


    def testDuration(self):
        # Chat without messages -> duration == n/a
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')

        # only client chatted -> duration == 0
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        chatter1 = Participant.objects.create(conversation=c2, name='Chatter1', role=Participant.ROLE_CLIENT)
        ChatMessage.objects.create(conversation=c2, sender=chatter1, event='message', created_at=datetime(2011, 11, 1, 17, 1), body='message text')

        # only staff chatted -> duration == 0
        c3 = Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 0), subject='Chat')
        staff1 = Participant.objects.create(conversation=c3, name='Staff1', role=Participant.ROLE_STAFF)
        ChatMessage.objects.create(conversation=c3, sender=staff1, event='message', created_at=datetime(2011, 11, 1, 18, 1), body='message text')

        # client and staff chatted
        c4 = Chat.objects.create(start_time=datetime(2011, 11, 1, 19, 0), subject='Chat')
        chatter2 = Participant.objects.create(conversation=c4, name='Chatter2', role=Participant.ROLE_CLIENT)
        staff2 = Participant.objects.create(conversation=c4, name='Staff2', role=Participant.ROLE_STAFF)
        ChatMessage.objects.create(conversation=c4, sender=chatter2, event='message', created_at=datetime(2011, 11, 1, 19, 1), body='message text')
        ChatMessage.objects.create(conversation=c4, sender=staff2, event='message', created_at=datetime(2011, 11, 1, 19, 2), body='message text')


        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), ['-', 0, 0, 60]):
            self.assertEqual(actual['avgChatTime'], expected)

