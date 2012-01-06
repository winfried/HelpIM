import datetime

from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext as _

from helpim.common.models import EventLog
from helpim.conversations.models import Chat
from helpim.stats import StatsProvider, EventLogFilter, EventLogProcessor
from helpim.utils import OrderedDict, total_seconds


class ChatHourlyStatsProvider(StatsProvider):
    knownStats = {'date': _('Date'),
                  'hour': _('Hour'),
                  'totalCount': _('Total Chats'),
                  'uniqueIPs': _('Unique IPs'),
                  'questionnairesSubmitted': _('Questionnaires'),
                  'blocked': _('Blocked'),
                  'assigned': _('Assigned'),
                  'interaction': _('Interaction'),
                  'queued': _('Queued'),
                  'avgWaitTime': _('Avg. Wait time (sec.)'),
                  'avgChatTime': _('Avg. Chat Time (sec.)') }

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
                for v in ['totalCount', 'uniqueIPs', 'questionnairesSubmitted', 'blocked', 'assigned', 'interaction', 'queued', 'avgWaitTime', 'avgChatTime', 'numChatTime']:
                    dictStats[chat.hourAgg][v] = 0
                dictStats[chat.hourAgg]['avgWaitTime'] = '-'

            dictStats[chat.hourAgg]['date'], dictStats[chat.hourAgg]['hour'] = chat.hourAgg.split(" ")

            try:
                dictStats[chat.hourAgg]['date'] = datetime.datetime.strptime(dictStats[chat.hourAgg]['date'], '%Y-%m-%d').date()
                dictStats[chat.hourAgg]['hour'] = int(dictStats[chat.hourAgg]['hour'])
            except:
                pass

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
                dictStats[chat.hourAgg]['avgChatTime'] += int(total_seconds(duration))
                dictStats[chat.hourAgg]['numChatTime'] += 1

            # count this Chat object
            dictStats[chat.hourAgg]['totalCount'] += 1


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


        # process EventLogs
        EventLogProcessor(listOfEvents, [WaitingTimeFilter()]).run(dictStats)

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

    @classmethod
    def get_detail_url(cls):
        return reverse('admin:conversations_conversation_changelist') + '?start_time__year=%(year)s&start_time__month=%(month)s&start_time__day=%(day)s'


class WaitingTimeFilter(EventLogFilter):
    """
    Determines waiting time careseeker experienced. Since the 'queued' stat derives from the waiting time, the 'queued' stat is also calculated here.
    """

    # amount of time in seconds user must have been waiting in line until considered 'queued'
    QUEUED_TRESHOLD = 15

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
        waitTime = int(total_seconds(self.waitEnd - self.waitStart))

        # default value is '-', displayed if no data for waitingTime were available from EventLogs
        if isinstance(result['avgWaitTime'], int):
            result['avgWaitTime'] = (result['avgWaitTime'] + waitTime) / 2
        else:
            result['avgWaitTime'] = waitTime

        # calculate 'queued' stat
        if waitTime >= WaitingTimeFilter.QUEUED_TRESHOLD:
            result['queued'] += 1

    def hasResult(self):
        return (not self.waitStart is None) and (not self.waitEnd is None) and (not self.key is None)

    def getKey(self):
        return self.key
