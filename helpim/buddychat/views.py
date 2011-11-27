from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

def welcome(request):

    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('buddychat_profile'))
    else:
        return HttpResponseRedirect(reverse('auth_login'))

@login_required
def profile(request):

    return render_to_response(
        'buddychat/welcome.html',
        context_instance=RequestContext(request)
        )
