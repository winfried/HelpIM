from django.conf.urls.defaults import *

urlpatterns = patterns(
    '',
    url(r'^$', 'helpim.buddychat.views.welcome'),
    url(r'^accounts/', include('registration.backends.default.urls')),
    )
