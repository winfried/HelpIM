from datetime import datetime

from django.contrib.auth.models import ContentType, Permission, User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from django.utils import html

from helpim.common.models import EventLog
from helpim.conversations.models import Chat, Participant, ChatMessage
from helpim.questionnaire.models import ConversationFormEntry, Questionnaire

from forms_builder.forms.models import FormEntry


def createEventLog(created_at, **kwargs):
    '''Creates a new EventLog and circumvents the ``auto_now_add`` option on the ``created_at`` field, so that there are fixed date values.'''
    newEvent = EventLog.objects.create(created_at=created_at, **kwargs)
    newEvent.created_at = created_at
    newEvent.save()
    
    return newEvent

class ChatHourlyStatsProviderTestCase(TestCase):
    def setUp(self):
        super(ChatHourlyStatsProviderTestCase, self).setUp()
        
        self.c = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'test')
        c, created = ContentType.objects.get_or_create(model='', app_label='stats',
                                                       defaults={'name': 'stats'})
        p, created = Permission.objects.get_or_create(codename='can_view_stats', content_type=c,
                                                      defaults={'name': 'Can view Stats', 'content_type': c})
        self.user.user_permissions.add(p)
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


    def testTotalCount(self):
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 10), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0), subject='Chat')
        Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 59), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 0), subject='Chat')

        Chat.objects.create(start_time=datetime(2011, 11, 11, 18, 0), subject='Chat')
        
        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])
        
        # total number of Chat objects
        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [2, 2, 1, 1]):
            self.assertEqual(actual['totalCount'], expected)


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


    def testQueued(self):
        '''
        This stat describes whether careseekers was in the waiting queue or not. Since all careseekers go to the waiting queue at least for a very short time,
        we rely on the waiting time and consider waiting times longer than 15s as "queued".
        '''

        # 10 seconds waiting time -> not 'queued'
        chat1 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0, 10), subject='Chat')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 0), type='helpim.rooms.waitingroom.joined', session='aabbccdd')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 0, 10), type='helpim.rooms.waitingroom.left', session='aabbccdd')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 0, 10), type='helpim.rooms.one2one.client_joined', session='aabbccdd', payload=chat1.id)

        # 25 seconds waiting time -> 'queued'
        chat2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 17, 0, 25), subject='Chat')
        createEventLog(created_at=datetime(2011, 11, 1, 17, 0), type='helpim.rooms.waitingroom.joined', session='aabbccdd')
        createEventLog(created_at=datetime(2011, 11, 1, 17, 0, 25), type='helpim.rooms.waitingroom.left', session='aabbccdd')
        createEventLog(created_at=datetime(2011, 11, 1, 17, 0, 25), type='helpim.rooms.one2one.client_joined', session='aabbccdd', payload=chat2.id)

        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])

        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [0, 1]):
            self.assertEqual(actual['queued'], expected)


    def testWaitingTime(self):
        '''
        Measure time users have to wait until Chat is successfully established. Do not regard users that left before.
        If a questionnaire was presented, waiting time starts after careseeker has questionnaire submitted.
        '''

        # 90 seconds waiting time, successfully established one2one chat
        chat1 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 1, 30), subject='Chat')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 0), type='helpim.rooms.waitingroom.joined', session='aabbccdd')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 1, 30), type='helpim.rooms.waitingroom.left', session='aabbccdd')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 1, 30), type='helpim.rooms.one2one.client_joined', session='aabbccdd', payload=chat1.id)

        # 30 seconds waiting time, successfully established one2one chat
        chat2 = Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 30, 30), subject='Chat')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 30), type='helpim.rooms.waitingroom.joined', session='xxyyzz')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 30, 30), type='helpim.rooms.waitingroom.left', session='xxyyzz')
        createEventLog(created_at=datetime(2011, 11, 1, 16, 30, 30), type='helpim.rooms.one2one.client_joined', session='xxyyzz', payload=chat2.id)

        # waiting time, but user left, doesn't count
        createEventLog(created_at=datetime(2011, 11, 1, 16, 45), type='helpim.rooms.waitingroom.joined', session='112233')

        # there needs to be a Chat object referenced in the EventLog, so this doesnt count
        createEventLog(created_at=datetime(2011, 11, 1, 17, 0), type='helpim.rooms.waitingroom.joined', session='AABBCC')
        createEventLog(created_at=datetime(2011, 11, 1, 17, 1, 30), type='helpim.rooms.waitingroom.left', session='AABBCC')
        createEventLog(created_at=datetime(2011, 11, 1, 17, 1, 30), type='helpim.rooms.one2one.client_joined', session='AABBCC')

        # Chat but there are no EventLogs, thus no data for waiting time
        Chat.objects.create(start_time=datetime(2011, 11, 1, 18, 15), subject='Chat')

        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))
        self.assertIsNotNone(response.context['aggregatedStats'])
        self.assertEqual(len(response.context['aggregatedStats'].keys()), 2)

        for actual, expected in zip(response.context['aggregatedStats'].itervalues(), [60, "-"]):
            self.assertEqual(actual['avgWaitTime'], expected)


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


    def testFirstColumnDetailLink(self):
        '''first column links to conversation admin showing conversations of that day'''

        Chat.objects.create(start_time=datetime(2011, 11, 1, 16, 0), subject='Chat')

        response = self.c.get(reverse('stats_overview', args=['chat', 2011]))

        # response will contain the link in escaped format
        self.assertContains(response, html.escape("?start_time__year=2011&start_time__month=11&start_time__day=1"), 1)
