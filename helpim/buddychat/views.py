from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext

def welcome(request):

    if request.user.is_authenticated():
        return render_to_response(
            'buddychat/welcome.html',
            context_instance=RequestContext(request)
            )
    else:
        return HttpResponseRedirect(reverse('auth_login'))
