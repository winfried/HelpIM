from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import redirect_to
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('')

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^admin/translate/', include('rosetta.urls')),
    )

js_info_dict = {
    'packages': ('helpim',),
}

urlpatterns += patterns(
    '',

    url(r'^$', 'helpim.rooms.views.client_join_chat', name='client_join_chat'),

    url(r"^forms/entry/(?P<form_entry_id>.*)/$", "helpim.questionnaire.views.form_entry", name="form_entry"),
    url(r"^forms/entry/(?P<form_entry_id>.*)/edit$", "helpim.questionnaire.views.form_entry_edit", name="form_entry_edit"),
    url(r"^forms/(?P<slug>.*)/(?P<entry>.*)/sent/$", "helpim.questionnaire.views.form_sent", kwargs={'template':'questionnaire/form_sent.html'}, name="form_sent"),
    url(r"^forms/(?P<slug>.*)/$", "helpim.questionnaire.views.form_detail", name="form_detail"),

    url(r'^login/?$', redirect_to, {'url': '/admin/'}),
    url(r'^login/$', 'django.contrib.auth.views.login'),
    url(r'^admin/stats/', include('helpim.stats.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/threadedcomments/', include('threadedcomments.urls')),
    url(r'^admin/rooms/join/(\d+)/$', 'helpim.rooms.views.staff_join_chat', name='staff_join_room_specific'),
    url(r'^admin/rooms/join/$', 'helpim.rooms.views.staff_join_chat', name='staff_join_room'),

    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
)
