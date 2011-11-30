import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response

from helpim.conversations.models import Conversation
from helpim.utils import OrderedDict


@login_required
def stats_overview(request, year=None):
    """Display tabular stats about conversations"""

    # default to current year
    if year is None:
        year = datetime.datetime.now().year

    try:
        year = int(year)
    except ValueError:
        year = datetime.datetime.now().year
    

    # list of years with Conversations needed for navigation
    listOfYears = Conversation.objects.getConversationYears()

    # get index of current year in listOfYears
    currentYearIndex = next((index for (index, x) in enumerate(listOfYears) if x["year"] == year), None)

    if currentYearIndex is not None:
        prevYearIndex = currentYearIndex - 1 if currentYearIndex > 0 else None
        nextYearIndex = currentYearIndex + 1 if currentYearIndex < len(listOfYears) - 1 else None


    # generate stats about current year's Conversations
    currentYearConversations = Conversation.objects.getConversations(year)
    dictStats = OrderedDict()

    for conv in currentYearConversations:
        clientParticipant = conv.getClient()
        staffParticipant = conv.getStaff()
        
        if conv.hourAgg not in dictStats:
            dictStats[conv.hourAgg] = _generateStatsDict()

        dictStats[conv.hourAgg]['date'], dictStats[conv.hourAgg]['hour'] = conv.hourAgg.split(" ")
        
        # total number of Conversations
        dictStats[conv.hourAgg]['totalCount'] += 1
        
        if not clientParticipant is None:
            # track unique IPs, unless there was no Participant in the Conversation
            if clientParticipant.ip_hash not in dictStats[conv.hourAgg]['ipTable']:
                dictStats[conv.hourAgg]['ipTable'][clientParticipant.ip_hash] = 0

            # was client Participant blocked?
            if clientParticipant.blocked is True:
                dictStats[conv.hourAgg]['blocked'] += 1
                
        if conv.hasQuestionnaire():
            dictStats[conv.hourAgg]['questionnairesSubmitted'] += 1
        
        #TODO: full
        
        #TODO: queued
        
        # staff member assigned to this Conversation?
        if not staffParticipant is None:
            dictStats[conv.hourAgg]['assigned'] += 1
        
        # did both Participants chat?
        if conv.hasInteraction():
            dictStats[conv.hourAgg]['interaction'] += 1
            
        # waiting time
        dictStats[conv.hourAgg]['avgWaitTime'] += conv.waitingTime()
        dictStats[conv.hourAgg]['numWaitTime'] += 1
        
        # chatting time
        duration = conv.duration()
        if isinstance(duration, datetime.timedelta):
            dictStats[conv.hourAgg]['avgChatTime'] += int(duration.total_seconds())
            dictStats[conv.hourAgg]['numChatTime'] += 1
            

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
        
        # calc avg chat time
        try:
            dictStats[key]['avgChatTime'] = dictStats[key]['avgChatTime'] / dictStats[key]['numChatTime']
        except ZeroDivisionError:
            dictStats[key]['avgChatTime'] = "-"
            
    
    return render_to_response("stats/stats_overview.html", {
        'currentYear': listOfYears[currentYearIndex] if not currentYearIndex is None else None,
        'prevYear': listOfYears[prevYearIndex] if not prevYearIndex is None else None,
        'nextYear': listOfYears[nextYearIndex] if not nextYearIndex is None else None,
        'conversationYears': listOfYears,
        'conversationStats': dictStats })


def _generateStatsDict():
    return {'date': '', 'hour': 0, 'totalCount': 0, 'ipTable': {}, 'uniqueIPs': 0,
            'questionnairesSubmitted': 0, 'blocked': 0, 'full': 0, 'queue': 0, 'assigned': 0, 'interaction': 0,
            'avgWaitTime': 0, 'numWaitTime': 0, 'avgChatTime': 0, 'numChatTime': 0}