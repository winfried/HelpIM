from django.conf.urls.defaults import patterns, include, url
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('')

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^admin/translate/', include('rosetta.urls')),
    )

urlpatterns += patterns('',
    # Examples:
    # url(r'^$', 'helpim.views.home', name='home'),
    # url(r'^helpim/', include('helpim.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^$', 'helpim.rooms.views.client_join_chat', name='client_join_chat'),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/threadedcomments/', include('threadedcomments.urls')),
    url(r'^admin/rooms/join/one2oneroom/$', 'helpim.rooms.views.staff_join_chat', name='staff_join_next_available_chat'),
    url(r'^admin/rooms/join/one2oneroom/(\d+)/$', 'helpim.rooms.views.staff_join_chat', name='staff_join_specific_chat'),

)
