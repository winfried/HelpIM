from django.http import HttpResponse
from helpim.rooms.models import One2OneRoom, AccessToken, Participant
from django.shortcuts import get_object_or_404, redirect
from django.utils.simplejson import dumps
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render_to_response
from django.forms import Form, CharField
from django.core.context_processors import csrf

@login_required
def staff_join_chat(request, room_pk=None):
    at = AccessToken.create(Participant.ROLE_STAFF)

    return render_to_response(
      'rooms/staff_join_chat.html', {
      'debug': settings.DEBUG,
      'xmpptk_config': dumps(dict({
                'muc_nick': request.user.username,
                'logout_redirect': request.META.get('HTTP_REFERER'),
                'bot_jid': '%s@%s' % (settings.BOT['connection']['username'], settings.BOT['connection']['domain']),
                'bot_nick': settings.BOT['muc']['nick'],
                'static_url': settings.STATIC_URL,
                'is_one2one': True,
                'is_staff': True,
                'token': at.token,
      }.items() + settings.CHAT.items()), indent=2)
    })

class GetClientNickForm(Form):
    nick = CharField(max_length=40)
    subject = CharField(max_length=64)

def client_join_chat(request):
    if request.COOKIES.has_key('room_token'):
        token = request.COOKIES.get('room_token')
        nick = request.COOKIES.get('room_nick')
        subject = request.COOKIES.get('room_subject')
    else:
        if request.method != 'POST':
            form = GetClientNickForm()
        else:
            form = GetClientNickForm(request.POST)

        if not form.is_valid():
            c = { 'form': form }
            c.update(csrf(request))
            return render_to_response('rooms/client_get_info.html', c)
        nick = form.cleaned_data['nick']
        subject = form.cleaned_data['subject']

        # must be done after form is checked otherwise token would be created at each request
        token = AccessToken.create().token

    return render_to_response(
      'rooms/client_join_chat.html', {
      'debug': settings.DEBUG,
      'xmpptk_config': dumps(dict({
                'muc_nick': nick,
                'muc_subject': subject,
                'logout_redirect': '/rooms/logged_out/',
                'bot_jid': '%s@%s' % (settings.BOT['connection']['username'], settings.BOT['connection']['domain']),
                'bot_nick': settings.BOT['muc']['nick'],
                'static_url': settings.STATIC_URL,
                'is_one2one': True,
                'is_staff': False,
                'token': token,
      }.items() + settings.CHAT.items()), indent=2)
    })

def client_logged_out(request):
    return render_to_response('rooms/client_logged_out.html', {});

def client_room_unavailable(request):
    return render_to_response('rooms/client_room_unavailable.html', {});
