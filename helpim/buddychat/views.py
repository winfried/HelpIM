from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _

from helpim.buddychat.models import BuddyChatProfile

def welcome(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('buddychat_profile', args=[request.user]))
    else:
        return HttpResponseRedirect(reverse('auth_login'))

@login_required
def profile(request, username):
    client = get_object_or_404(BuddyChatProfile, user__username = username)

    if request.user.has_perm('buddychat.is_coordinator') or (request.user.has_perm('buddychat.is_volunteer') and request.user == client.volunteer) or request.user == client.user:
        return render_to_response(
            'buddychat/profile.html',
            {'client': client},
            context_instance=RequestContext(request)
            )
    return HttpResponse(_('Access Denied'))
