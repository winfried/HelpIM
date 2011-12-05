import datetime

from django.db import models
from django.utils.translation import ugettext as _

from helpim.stats import StatsProvider
from helpim.conversations.models import Chat
from helpim.utils import OrderedDict


class ChatStatsProvider(StatsProvider):
    knownStats = {'date': _('Date'),
                  'hour': _('Hour'),
                  'uniqueIPs': _('Unique IPs'),
                  'questionnairesSubmitted': _('Questionnaires'),
                  'blocked': _('Blocked'),
                  'full': _('Full'),
                  'queue': _('Queue'),
                  'assigned': _('Assigned'),
                  'interaction': _('Interaction'),
                  'avgWaitTime': _('Avg. Wait time'),
                  'avgChatTime': _('Avg. Chat Time') }

    @classmethod
    def render(cls, listOfChats):
        dictStats = OrderedDict()

        for chat in listOfChats:
            clientParticipant = chat.getClient()
            staffParticipant = chat.getStaff()

            if chat.hourAgg not in dictStats:
                # insertion order matters
                dictStats[chat.hourAgg] = OrderedDict()
                dictStats[chat.hourAgg]['date'] = ''
                dictStats[chat.hourAgg]['hour'] = 0
                dictStats[chat.hourAgg]['ipTable'] = {}
                for v in ['uniqueIPs', 'questionnairesSubmitted', 'blocked', 'full', 'queue', 'assigned', 'interaction', 'avgWaitTime', 'numWaitTime', 'avgChatTime', 'numChatTime']:
                    dictStats[chat.hourAgg][v] = 0

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

            #TODO: full

            #TODO: queued

            # staff member and client assigned to this Conversation?
            if not staffParticipant is None and not clientParticipant is None:
                dictStats[chat.hourAgg]['assigned'] += 1

            # did both Participants chat?
            if chat.hasInteraction():
                dictStats[chat.hourAgg]['interaction'] += 1

            # waiting time
            dictStats[chat.hourAgg]['avgWaitTime'] += chat.waitingTime()
            dictStats[chat.hourAgg]['numWaitTime'] += 1

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

            # calc avg wait time
            try:
                dictStats[key]['avgWaitTime'] = dictStats[key]['avgWaitTime'] / dictStats[key]['numWaitTime']
            except ZeroDivisionError:
                dictStats[key]['avgWaitTime'] = '-'
            del dictStats[key]['numWaitTime']

            # calc avg chat time
            try:
                dictStats[key]['avgChatTime'] = dictStats[key]['avgChatTime'] / dictStats[key]['numChatTime']
            except ZeroDivisionError:
                dictStats[key]['avgChatTime'] = "-"
            del dictStats[key]['numChatTime']

        return dictStats


    @classmethod
    def countObjects(cls):
        """Returns list with years and number of Chats during year"""

        # see: https://code.djangoproject.com/ticket/10302
        extra_mysql = {"value": "YEAR(start_time)"}
        return Chat.objects.extra(select=extra_mysql).values("value").annotate(count=models.Count('id')).order_by('start_time')


    @classmethod
    def aggregateObjects(cls, whichYear):
        """Returns Conversations of year specified"""
        return Chat.objects.filter(start_time__year=whichYear).extra(select={"hourAgg": "LEFT(start_time, 13)"}).order_by('start_time')
