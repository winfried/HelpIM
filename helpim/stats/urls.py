from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'helpim.stats.views',    
    url(r'^(?P<keyword>.+)/(?P<year>\d{4})$', 'stats_overview', name='stats_overview'),
    url(r'^(?P<keyword>.+)$', 'stats_overview', name='stats_overview'),
)