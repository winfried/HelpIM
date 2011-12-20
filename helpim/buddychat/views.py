from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

def welcome(request):

    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('buddychat_profile', args=[request.user]))
    else:
        return HttpResponseRedirect(reverse('auth_login'))

@login_required
def profile(request, username):
        return render_to_response(
            'buddychat/profile.html',
            {'username': username},
            context_instance=RequestContext(request)
            )
    
