import csv
import datetime
import xlwt

from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from helpim.conversations.stats import ChatHourlyStatsProvider, ChatFlatStatsProvider
from helpim.stats.forms import ReportForm
from helpim.stats.models import Report

@permission_required('stats.can_view_stats', '/admin')
def stats_overview(request, keyword, year=None, format=None):
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

    insertIndex = 0
    currentPageIndex = None
    
    # try to find index of requested year in `listOfPages`. also determine insert position if requested year is not in that list.
    for (idx, x) in enumerate(listOfPages):
        # get index of current year in listOfPages
        if x['value'] == year:
            currentPageIndex = idx
        
        # find largest value that is smaller than requested year, insert after that index
        # if no such value exists, use default insertIndex of 0
        if x['value'] < year:
            insertIndex = idx + 1
        
    # requested year is not in list, "fake" add it
    if currentPageIndex is None:
        listOfPages.insert(insertIndex, {'count': 0, 'value': year})
        currentPageIndex = insertIndex
    
    # derive "prev" and "next" indices, if possible
    if currentPageIndex is not None:
        prevPageIndex = currentPageIndex - 1 if currentPageIndex > 0 else None
        nextPageIndex = currentPageIndex + 1 if currentPageIndex < len(listOfPages) - 1 else None
    else:
        prevPageIndex = None
        nextPageIndex = None

    # generate stats about current year's Conversations
    currentYearChats = statsProvider.aggregateObjects(year)
    dictStats = statsProvider.render(currentYearChats)

    # output data in format according to parameter in url
    if format == 'csv':
        return _stats_overview_csv(statsProvider.knownStats, dictStats, keyword, year)
    elif format == 'xls':
        return _stats_overview_xls(statsProvider.knownStats, dictStats, keyword, year)
    else:
        return render_to_response("stats/stats_overview.html",
            {'statsKeyword': keyword,
            'statsShortName': statsProvider.get_short_name(),
            'statsLongName': statsProvider.get_long_name(),
            'detail_url': statsProvider.get_detail_url(),
            'currentPage': listOfPages[currentPageIndex] if not currentPageIndex is None else {'count': 0, 'value': year},
            'prevPage': listOfPages[prevPageIndex] if not prevPageIndex is None else None,
            'nextPage': listOfPages[nextPageIndex] if not nextPageIndex is None else None,
            'pagingYears': listOfPages,
            'knownStats': statsProvider.knownStats,
            'aggregatedStats': dictStats },
            context_instance=RequestContext(request))


@permission_required('stats.can_view_stats', '/admin')
def stats_index(request):
    '''Display overview showing available StatProviders'''

    listOfStatsProviders = []
    for keyword, provider in _getStatsProviders().iteritems():
        listOfStatsProviders.append({
            'keyword': keyword,
            'short_name': provider.get_short_name(),
            'long_name': provider.get_long_name()
        })

    return render_to_response('stats/stats_index.html',
        {
          'statProviders': listOfStatsProviders,
          'reports': Report.objects.all()
        },
        context_instance=RequestContext(request))

@permission_required('stats.can_view_stats', '/admin')
def report_new(request):
    '''display form where new Report can be configured'''
    
    context = {}
    
    if request.method == 'POST':
        report_form = ReportForm(request.POST)
        if report_form.is_valid():
            if len(request.POST.get('action_preview', '')) > 0:
                # get Report object from ReportForm, unsaved
                report_obj = report_form.save(commit=False)
                context['rendered_report'] = _render_report(report_obj)
            elif len(request.POST.get('action_save', '')) > 0:
                report_obj = report_form.save()
                return HttpResponseRedirect(report_obj.get_absolute_url())
    else:    
        report_form = ReportForm()

    context['report_form'] = report_form
    
    return render_to_response('stats/report_new.html',
        context,
        context_instance=RequestContext(request)
    )

@permission_required('stats.can_view_stats', '/admin')
def report_show(request, id):
    '''generate and show pre-saved Report'''

    report = get_object_or_404(Report, pk=id)
    rendered_report = _render_report(report)

    return render_to_response('stats/report_show.html',
        {
          'report': report,
          'rendered_report': rendered_report,
        },
        context_instance=RequestContext(request)
    )

@permission_required('stats.can_view_stats', '/admin')
def report_delete(request, id):
    '''deletes a report'''

    report = get_object_or_404(Report, pk=id)
    report.delete()

    return HttpResponseRedirect(reverse('stats_index'))

def _render_report(report):
    list_of_chats = report.matching_chats()

    return { 'data': report.title }

def _stats_overview_csv(knownStats, dictStats, keyword, year):
    '''Creates a Response with the stat data rendered as comma-separated values (CSV)'''

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=stats.%s.%s.csv' % (keyword, year)

    # apparently, in this loop, datetime.date objects in dictStats are automatically formatted according to ISO
    # which is 'YYYY-MM-DD' and looks good in CSV
    
    writer = csv.writer(response)
    writer.writerow(knownStats.values())
    for statRow in dictStats.itervalues():
        writer.writerow([statRow.get(statName, '') for statName in knownStats.iterkeys()])

    return response


def _stats_overview_xls(knownStats, dictStats, keyword, year):
    '''Creates a Response with the stat data rendered in a MS Excel format'''

    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=stats.%s.%s.xls' % (keyword, year)

    # init sheet
    book = xlwt.Workbook()
    sheet = book.add_sheet('%s %s' % (keyword, year))

    # write heading row
    row, col = 0, 0
    for heading in knownStats.values():
        sheet.write(row, col, heading)
        col += 1

    # stat data after that
    row, col = 1, 0
    for statRow in dictStats.itervalues():
        for statName in knownStats.iterkeys():
            stat = statRow.get(statName, '')
            
            if isinstance(stat, datetime.date):
                style = xlwt.Style.XFStyle()
                style.num_format_str = 'YYYY-MM-DD'
            elif isinstance(stat, datetime.datetime):
                style = xlwt.Style.XFStyle()
                style.num_format_str = 'YYYY-MM-DD hh:mm:ss'
            else:
                style = xlwt.Style.default_style

            sheet.write(row, col, stat, style)
            col += 1
        row += 1
        col = 0

    book.save(response)
    return response


def _getStatsProviders():
    '''Maps stat keyword to corresponding StatsProvider -- for now in a static fashion'''
    return { 'chat': ChatHourlyStatsProvider,
             'chatflat': ChatFlatStatsProvider }


def _getStatsProvider(forName):
    '''find appropriate StatsProvider for given keyword'''

    forName = forName.lower()
    knownProviders = _getStatsProviders()

    if forName in knownProviders:
        return knownProviders[forName]
    else:
        return None
