from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'helpim.stats.views',
    
    # Reports
    url(r'^reports/new/$', 'report_new', name='report_new'),
    url(r'^reports/(?P<id>\d+)/$', 'report_show', name='report_show'),
    
    # Stats
    url(r'^(?P<keyword>.+)/(?P<year>\d{4})/(?P<format>.+)/$', 'stats_overview', name='stats_overview'),
    url(r'^(?P<keyword>.+)/(?P<year>\d{4})/$', 'stats_overview', name='stats_overview'),
    url(r'^(?P<keyword>.+)/$', 'stats_overview', name='stats_overview'),
    url(r'^$', 'stats_index', name='stats_index'),
)
