from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'helpim.stats.views',
    
    # Reports
    url(r'^reports/new/$', 'reports_new', name='reports_new'),
    url(r'^reports/(?P<id>\d+)/$', 'reports_show', name='reports_show'),
    
    # Stats
    url(r'^(?P<keyword>.+)/(?P<year>\d{4})/(?P<format>.+)/$', 'stats_overview', name='stats_overview'),
    url(r'^(?P<keyword>.+)/(?P<year>\d{4})/$', 'stats_overview', name='stats_overview'),
    url(r'^(?P<keyword>.+)/$', 'stats_overview', name='stats_overview'),
    url(r'^$', 'stats_index', name='stats_index'),
)
