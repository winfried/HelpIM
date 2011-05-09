from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'helpim.views.home', name='home'),
    # url(r'^helpim/', include('helpim.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/threadedcomments/', include('threadedcomments.urls')),
    url(r'^admin/rooms/join/one2oneroom/$', 'helpim.rooms.views.staff_join_chat', name='staff_join_next_available_chat'),
    url(r'^admin/rooms/join/one2oneroom/(\d+)/$', 'helpim.rooms.views.staff_join_chat', name='staff_join_specific_chat'),

    url(r'^rooms/join/$', 'helpim.rooms.views.client_join_chat', name='client_join_chat'),
    url(r'^rooms/unavailable/$', 'helpim.rooms.views.client_room_unavailable', name='client_room_unavailable'),
    url(r'^rooms/logged_out/$', 'helpim.rooms.views.client_logged_out', name='client_logged_out'),
)

from django.conf import settings
if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^admin/translate/', include('rosetta.urls')),
    )
