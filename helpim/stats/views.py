import datetime

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response

from helpim.conversations.stats import ChatStatsProvider

@login_required
def stats_overview(request, keyword, year=None):
    """Display tabular stats"""

    # find StatsProvider that will collect stats
    statsProvider = _getStatsProvider(keyword)
    if statsProvider is None:
        raise Http404('No stats for this keyword')

    # default to current year
    if year is None:
        year = datetime.datetime.now().year
    try:
        year = int(year)
    except ValueError:
        year = datetime.datetime.now().year


    # list of years with Conversations needed for navigation
    listOfPages = statsProvider.countObjects()

    # get index of current year in listOfPages
    currentPageIndex = next((index for (index, x) in enumerate(listOfPages) if x["value"] == year), None)

    if currentPageIndex is not None:
        prevPageIndex = currentPageIndex - 1 if currentPageIndex > 0 else None
        nextPageIndex = currentPageIndex + 1 if currentPageIndex < len(listOfPages) - 1 else None
    else:
        prevPageIndex = None
        nextPageIndex = None

    # generate stats about current year's Conversations
    currentYearChats = statsProvider.aggregateObjects(year)
    dictStats = statsProvider.render(currentYearChats)

    # generate table header
    # look at dict of first entry and translate dict's keys
    if len(dictStats) > 0:
        tableHeadings = [statsProvider.getStatTranslation(h) for h in dictStats.items()[0][1].keys()]
    else:
        tableHeadings = []

    return render_to_response("stats/stats_overview.html", {
        'statsKeyword': keyword,
        'currentPage': listOfPages[currentPageIndex] if not currentPageIndex is None else {'count': 0, 'value': year},
        'prevPage': listOfPages[prevPageIndex] if not prevPageIndex is None else None,
        'nextPage': listOfPages[nextPageIndex] if not nextPageIndex is None else None,
        'pagingYears': listOfPages,
        'tableHeadings': tableHeadings,
        'aggregatedStats': dictStats })


def _getStatsProvider(forName):
    forName = forName.lower()

    if forName == u"chat":
        return ChatStatsProvider
    else:
        return None
