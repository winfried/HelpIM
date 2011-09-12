from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.simplejson import dumps
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render_to_response
from django.forms import Form, CharField
from django.core.context_processors import csrf

from helpim.rooms.models import One2OneRoomAccessToken, LobbyRoomAccessToken, Participant

@login_required
def staff_join_chat(request, room_pk=None):
    ref = request.META.get('HTTP_REFERER')
    proto = ref[:ref.find('://')]
    return join_chat(
        request,
        dict({
                'muc_nick': request.user.username,
                'logout_redirect': ref,
                'conversation_redirect': '%s://%s/admin/conversations/conversation/' % (proto, request.META.get('HTTP_HOST')),
                }),
        Participant.ROLE_STAFF
        )

def client_join_chat(request):
    return join_chat(
        request,
        dict({
                'logout_redirect': '/logged_out/',
                'unavailable_redirect': '/unavailable/',
                })
        )

@login_required
def join_lobby(request):
    token = LobbyRoomAccessToken.get_or_create(request.META.get('REMOTE_ADDR'), role, request.COOKIES.get('room_token'))

    return render_to_response(
      'rooms/join_chat.html', {
      'debug': settings.DEBUG,
      'is_staff': True,
      'xmpptk_config': dumps(dict({
                'muc_nick': request.user.username,
                'logout_redirect': request.META.get('HTTP_REFERER'),
                'bot_jid': '%s@%s' % (settings.BOT['connection']['username'], settings.BOT['connection']['domain']),
                'bot_nick': settings.BOT['muc']['nick'],
                'static_url': settings.STATIC_URL,
                'is_one2one': False,
                'is_staff': True,
                'token': token.token,
      }.items() + settings.CHAT.items()), indent=2)
    })

def join_chat(request, cfg, role=Participant.ROLE_CLIENT):

    token = One2OneRoomAccessToken.get_or_create(request.META.get('REMOTE_ADDR'), role, request.COOKIES.get('room_token'))
    if token is None:
        return render_to_response('rooms/blocked.html')

    return render_to_response(
      'rooms/join_chat.html', {
      'debug': settings.DEBUG,
      'is_staff': role is Participant.ROLE_STAFF,
      'xmpptk_config': dumps(dict({
                'logout_redirect': request.META.get('HTTP_REFERER'),
                'bot_jid': '%s@%s' % (settings.BOT['connection']['username'], settings.BOT['connection']['domain']),
                'bot_nick': settings.BOT['muc']['nick'],
                'static_url': settings.STATIC_URL,
                'is_one2one': True,
                'is_staff': role is Participant.ROLE_STAFF,
                'token': token.token,
      }.items() + settings.CHAT.items() + cfg.items()), indent=2)
    })    
