from datetime import datetime
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _

from helpim.buddychat.models import BuddyChatProfile

class ConvMessageForm(forms.Form):
    body = forms.CharField(max_length=4096, widget=forms.Textarea)

def welcome(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('buddychat_profile', args=[request.user]))
    else:
        return HttpResponseRedirect(reverse('auth_login'))

@login_required
def profile(request, username):
    client = get_object_or_404(BuddyChatProfile, user__username = username)
    if request.user.has_perm('buddychat.is_coordinator') or (request.user.has_perm('buddychat.is_careworker') and request.user == client.volunteer) or request.user == client.user:
        if request.method == "POST":
            form = ConvMessageForm(request.POST)
            if form.is_valid():
                conv = {
                    'careworker': client.careworker_conversation,
                    'coordinator': client.coordinator_conversation,
                    'careworker_coordinator': client.careworker_coordinator_conversation
                    }
                conv[request.POST['conv']].messages.create(
                    body = form.cleaned_data['body'],
                    sender = conv[request.POST['conv']].get_or_create_participant(request.user),
                    sender_name = request.user.username,
                    created_at = datetime.now()
                    )
                form = ConvMessageForm()
        else:
            form = ConvMessageForm()
        params = {'client': client,
                  'form': form}
        if request.user.has_perm('buddychat.is_coordinator'):
            params['careworkers'] = User.objects.filter(groups__name='careworkers')

        return render_to_response(
            'buddychat/profile.html',
            params,
            context_instance=RequestContext(request)
            )
    else: 
        return HttpResponse(_('Access Denied'))
