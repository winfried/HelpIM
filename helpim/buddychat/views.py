from datetime import datetime
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.simplejson import dumps
from django.utils.translation import ugettext as _

from hashlib import md5

from helpim.buddychat.models import BuddyChatProfile
from helpim.questionnaire.models import Questionnaire
from helpim.rooms.models import AccessToken, SimpleRoomToken, Participant, SimpleRoom

class ConvMessageForm(forms.Form):
    body = forms.CharField(max_length=4096, widget=forms.Textarea)

class CareworkersForm(forms.Form):
    choices = [('', _('None'))]
    careworkers = User.objects.filter(groups__name='careworkers')
    for user in careworkers:
        choices.append((user.pk, user.username))
    careworker = forms.ChoiceField(choices=choices, required=False)

def welcome(request):
    if request.user.is_authenticated():
        if request.user.is_staff:
            """ staff doesn't have a profile - redirect to admin """
            return HttpResponseRedirect(reverse('admin:index'))
        else:
            return HttpResponseRedirect(reverse('buddychat_profile', args=[request.user]))
    else:
        return HttpResponseRedirect(reverse('auth_login'))

@login_required(login_url='/login/')
def profile(request, username):
    client = get_object_or_404(BuddyChatProfile, user__username = username)
    if request.user == client.user and not client.ready:
        try:
            q = Questionnaire.objects.filter(position='CR')[0]
            return HttpResponseRedirect(q.get_absolute_url())
        except IndexError:
            pass
    if request.user.has_perm('buddychat.is_coordinator') or (request.user.has_perm('buddychat.is_careworker') and request.user == client.careworker) or request.user == client.user:
        """ we need to make sure requesting user is either
        * the careseeker himself (aka the 'client')
        * the careworker associated with this client
        * a coordinator
        """
        if request.method == "POST":
            form = ConvMessageForm(request.POST)
            if form.is_valid():
                """
                POST var 'conv' decides which conversation we're acting on
                """
                conv = {
                    'careworker': client.careworker_conversation,
                    'coordinator': client.coordinator_conversation,
                    'careworker_coordinator': client.careworker_coordinator_conversation
                    }[request.POST['conv']]

                """
                check whether user is allowed to act on this conversation according to this rules
                * careseeker allowed to post to careworker and coordinator
                * careworker allowed to post to careworker and careworker_coordinator
                * coordinator allowed to post to coordinator and careworker_coordinator
                and set rcpt for email notification
                """
                rcpt = None # rcpt is None for coordinators
                if conv is client.careworker_conversation:
                    if not client.careworker:
                        return HttpResponse(_('Access Denied'))
                    elif request.user == client.user:
                        rcpt = client.careworker
                    elif request.user == client.careworker:
                        rcpt = client.user
                    else:
                        return HttpResponse(_('Access Denied'))
                elif conv is client.coordinator_conversation:
                    if request.user.has_perm('buddychat.is_coordinator'):
                        rcpt = client.user
                    elif request.user != client.user:
                        return HttpResponse(_('Access Denied'))
                elif conv is client.careworker_coordinator_conversation:
                    if request.user.has_perm('buddychat.is_coordinator'):
                        rcpt = client.careworker
                    elif request.user != client.careworker:
                        return HttpResponse(_('Access Denied'))

                conv.messages.create(
                    body = form.cleaned_data['body'],
                    sender = conv.get_or_create_participant(request.user),
                    sender_name = request.user.username,
                    created_at = datetime.now()
                    )
                """
                send email
                """
                if Site._meta.installed:
                    site = Site.objects.get_current()
                else:
                    site = RequestSite(request)

                subject = _('a message from %s' % request.user.username)
                body = _('%s wrote a message on %s\'s profile:\n\n%s\n\nDon\'t reply to this message directly, reply on this user\'s personal page at http://%s/profile/%s/' % (request.user.username, client.user.username, form.cleaned_data['body'], site, client.user.username))

                if not rcpt is None:
                    rcpt.email_user(subject, body)
                else:
                    coordinators = User.objects.filter(groups__name='coordinators')
                    for user in coordinators:
                        user.email_user(subject, body)

                messages.success(request, _('Your message has been sent'))
                form = ConvMessageForm() # reset form
        else:
            form = ConvMessageForm()
        params = {'client': client,
                  'form': form}
        if request.user.has_perm('buddychat.is_coordinator'):
            if client.careworker:
                params['careworkers_form'] = CareworkersForm(initial={'careworker': client.careworker.pk})
            else:
                params['careworkers_form'] = CareworkersForm()

        return render_to_response(
            'buddychat/profile.html',
            params,
            context_instance=RequestContext(request)
            )
    else:
        return HttpResponse(_('Access Denied'))

@permission_required('buddychat.is_coordinator')
def set_cw(request, username):
    """ set a careworker """
    client = get_object_or_404(BuddyChatProfile, user__username = username)
    if request.method == "POST":
        form = CareworkersForm(request.POST)
        if form.is_valid():
            try:
                careworker = User.objects.get(pk=form.cleaned_data['careworker'])
            except ValueError:
                careworker = None
            except User.DoesNotExist:
                careworker = None
                messages.info(request, _('Careworker not found'))
            if client.careworker != careworker:
                client.careworker = careworker
                if not client.careworker is None:
                    client.coupled_at = datetime.now()
                    messages.success(request, _('Careworker has been set'))
                else:
                    client.coupled_at = None
                    messages.success(request, _('Careworker has been unset'))
                client.save()

    return HttpResponseRedirect(reverse('buddychat_profile', args=[username]))

@login_required(login_url='/login/')
def join_chat(request, username):
    client = get_object_or_404(BuddyChatProfile, user__username = username)

    if request.user != client.user and request.user != client.careworker:
        """ only careworkers and the client itself are allowed to access the chat """
        return HttpResponse(_('Access Denied'))
        
    is_staff = client.careworker == request.user
    if is_staff:
        role = Participant.ROLE_STAFF
    else:
        role = Participant.ROLE_CLIENT

    ac = AccessToken.objects.get_or_create(token=request.COOKIES.get('room_token'), role=role, ip_hash=md5(request.META.get('REMOTE_ADDR')).hexdigest(), created_by=request.user)
    if client.room is None or client.room.getStatus() != 'waiting':
        client.room = SimpleRoom.objects.filter(status='available')[0]
        client.save()

    # delete old SimpleRoomTokens
    SimpleRoomToken.objects.filter(token=ac).all().delete()

    # store room with SimpleRoomToken
    SimpleRoomToken.objects.get_or_create(token = ac, room=client.room)
    
    return render_to_response(
        'rooms/join_chat.html', {
            'debug': settings.DEBUG,
            'is_staff': is_staff,
            'is_one2one': True,
            'xmpptk_config': dumps(dict({
                'logout_redirect': request.META.get('HTTP_REFERER'),
                'bot_jid': '%s@%s/%s' % (settings.BOT['connection']['username'],
                                         settings.BOT['connection']['domain'],
                                         settings.BOT['connection']['resource']),
                'bot_nick': settings.BOT['muc']['nick'],
                'static_url': settings.STATIC_URL,
                'is_staff':is_staff,
                'token': ac.token,
                'muc_nick': request.user.username,
                'mode': 'light',
                }.items() + settings.CHAT.items()), indent=2)
            })
