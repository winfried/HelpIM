import datetime

from django.db import models
from django.utils.translation import ugettext as _

from helpim.common.models import EventLog
from helpim.conversations.models import Chat
from helpim.stats import StatsProvider
from helpim.utils import OrderedDict


class ChatStatsProvider(StatsProvider):
    knownStats = {'date': _('Date'),
                  'hour': _('Hour'),
                  'uniqueIPs': _('Unique IPs'),
                  'questionnairesSubmitted': _('Questionnaires'),
                  'blocked': _('Blocked'),
                  'assigned': _('Assigned'),
                  'interaction': _('Interaction'),
                  'avgWaitTime': _('Avg. Wait time'),
                  'avgChatTime': _('Avg. Chat Time') }

    @classmethod
    def render(cls, listOfObjects):
        dictStats = OrderedDict()

        listOfChats, listOfEvents = listOfObjects

        for chat in listOfChats:
            clientParticipant = chat.getClient()
            staffParticipant = chat.getStaff()

            if chat.hourAgg not in dictStats:
                # insertion order matters
                dictStats[chat.hourAgg] = OrderedDict()
                dictStats[chat.hourAgg]['date'] = ''
                dictStats[chat.hourAgg]['hour'] = 0
                dictStats[chat.hourAgg]['ipTable'] = {}
                for v in ['uniqueIPs', 'questionnairesSubmitted', 'blocked', 'assigned', 'interaction', 'avgWaitTime', 'avgChatTime', 'numChatTime']:
                    dictStats[chat.hourAgg][v] = 0
                dictStats[chat.hourAgg]['avgWaitTime'] = '-'
                
            dictStats[chat.hourAgg]['date'], dictStats[chat.hourAgg]['hour'] = chat.hourAgg.split(" ")

            if not clientParticipant is None:
                # track unique IPs, unless there was no Participant in the Conversation
                if clientParticipant.ip_hash not in dictStats[chat.hourAgg]['ipTable']:
                    dictStats[chat.hourAgg]['ipTable'][clientParticipant.ip_hash] = 0

                # was client Participant blocked?
                if clientParticipant.blocked is True:
                    dictStats[chat.hourAgg]['blocked'] += 1

            if chat.hasQuestionnaire():
                dictStats[chat.hourAgg]['questionnairesSubmitted'] += 1

            # staff member and client assigned to this Conversation?
            if not staffParticipant is None and not clientParticipant is None:
                dictStats[chat.hourAgg]['assigned'] += 1

            # did both Participants chat?
            if chat.hasInteraction():
                dictStats[chat.hourAgg]['interaction'] += 1

            # chatting time
            duration = chat.duration()
            if isinstance(duration, datetime.timedelta):
                dictStats[chat.hourAgg]['avgChatTime'] += int(duration.total_seconds())
                dictStats[chat.hourAgg]['numChatTime'] += 1


        # post-processing
        for key in dictStats.iterkeys():
            # count unique IPs
            dictStats[key]['uniqueIPs'] = len(dictStats[key]['ipTable'].keys())
            del dictStats[key]['ipTable']

            # calc avg chat time
            try:
                dictStats[key]['avgChatTime'] = dictStats[key]['avgChatTime'] / dictStats[key]['numChatTime']
            except ZeroDivisionError:
                dictStats[key]['avgChatTime'] = "-"
            del dictStats[key]['numChatTime']


        # process EventLog
        currentSession = None
        wtProcessor = WaitingTimeProcessor()
        for event in listOfEvents:
            if currentSession != event.session:
                if wtProcessor.isValid():
                    key = wtProcessor.getKey()[:13]
                    if key in dictStats:
                        wtProcessor.addToResult(dictStats[key])

                wtProcessor.start()
                currentSession = event.session

            wtProcessor.processEvent(event)
        if wtProcessor.isValid():
            key = wtProcessor.getKey()[:13]
            if key in dictStats:
                wtProcessor.addToResult(dictStats[key])


        return dictStats


    @classmethod
    def countObjects(cls):
        """Returns list with years and number of Chats during year"""

        # see: https://code.djangoproject.com/ticket/10302
        extra_mysql = {"value": "YEAR(start_time)"}
        return Chat.objects.extra(select=extra_mysql).values("value").annotate(count=models.Count('id')).order_by('start_time')


    @classmethod
    def aggregateObjects(cls, whichYear):
        """Returns relevant Chats and Events of year specified"""
        return (Chat.objects.filter(start_time__year=whichYear).extra(select={"hourAgg": "LEFT(start_time, 13)"}).order_by('start_time'),
                EventLog.objects.findByYearAndTypes(whichYear, ['helpim.rooms.waitingroom.joined', 'helpim.rooms.waitingroom.left', 'helpim.rooms.one2one.client_joined']))


class WaitingTimeProcessor():
    def __init__(self):
        self.start()

    def start(self):
        self.waitStart = None
        self.waitEnd = None
        self.key = None

    def processEvent(self, event):
        if event.type == 'helpim.rooms.waitingroom.joined':
            self.waitStart = event.created_at
        elif event.type == 'helpim.rooms.waitingroom.left':
            self.waitEnd = event.created_at
        elif event.type == 'helpim.rooms.one2one.client_joined':
            self.key = str(event.created_at)

    def addToResult(self, result):
        waitTime = int((self.waitEnd - self.waitStart).total_seconds())

        # default value is '-', displayed if no data for waitingTime were available from EventLogs
        if isinstance(result['avgWaitTime'], int):
            result['avgWaitTime'] = (result['avgWaitTime'] + waitTime) / 2
        else:
            result['avgWaitTime'] = waitTime

    def isValid(self):
        return (not self.waitStart is None) and (not self.waitEnd is None) and (not self.key is None)

    def getKey(self):
        return self.key
