from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

from helpim.conversations.models import Chat, Participant


class StatsOverviewTestCase(TestCase):
    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'test')
        self.assertTrue(self.c.login(username=self.user.username, password='test'), 'Could not login')

    def testYearsPagination(self):
        c1 = Chat.objects.create(start_time=datetime(2008, 11, 1, 16, 0), subject='Chat')
        c2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 10), subject='Chat')
        c3 = Chat.objects.create(start_time=datetime(2013, 11, 1, 17, 0), subject='Chat')


        response = self.c.get('/admin/stats/2011')
        self.assertEqual(response.context['prevYear']['year'], 2008)
        self.assertEqual(response.context['currentYear']['year'], 2011)
        self.assertEqual(response.context['nextYear']['year'], 2013)
        for year, pageYear in zip([2008, 2011, 2013], response.context['conversationYears']):
            self.assertEqual(pageYear['year'], year)

        response = self.c.get('/admin/stats/2008')
        self.assertEqual(response.context['prevYear'], None)
        self.assertEqual(response.context['currentYear']['year'], 2008)
        self.assertEqual(response.context['nextYear']['year'], 2011)

        response = self.c.get('/admin/stats/2013')
        self.assertEqual(response.context['prevYear']['year'], 2011)
        self.assertEqual(response.context['currentYear']['year'], 2013)
        self.assertEqual(response.context['nextYear'], None)


    def testHourAggregation(self):
        '''Chats are aggregated by date and hour'''


        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 10), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 59), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 0), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 11, 18, 0), subject='Chat')


        response = self.c.get('/admin/stats/2011')
        self.assertIsNotNone(response.context['conversationStats'])

        self.assertEqual(len(response.context['conversationStats'].keys()), 4)
        self.assertEqual(response.context['conversationStats'].keys(), ['2011-11-01 16', '2011-11-01 17', '2011-11-01 18', '2011-11-11 18'])


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


        response = self.c.get('/admin/stats/2011')
        self.assertIsNotNone(response.context['conversationStats'])

        # total number of Chats
        for actual, expected in zip(response.context['conversationStats'].itervalues(), [2, 2, 1]):
            self.assertEqual(actual['totalCount'], expected)

        # unique Chatters
        for actual, expected in zip(response.context['conversationStats'].itervalues(), [1, 2, 0]):
            self.assertEqual(actual['uniqueIPs'], expected)


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


        response = self.c.get('/admin/stats/2011')
        self.assertIsNotNone(response.context['conversationStats'])

        for actual, expected in zip(response.context['conversationStats'].itervalues(), [1, 2, 0]):
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


        response = self.c.get('/admin/stats/2011')
        self.assertIsNotNone(response.context['conversationStats'])

        for actual, expected in zip(response.context['conversationStats'].itervalues(), [1, 0, 0]):
            self.assertEqual(actual['assigned'], expected)


    def testInteraction(self):
        pass


    def testWaitingTime(self):
        pass


    def testDuration(self):
        pass
