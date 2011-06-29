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
    return join_chat(
        request,
        dict({
            'muc_nick': request.user.username,
            'logout_redirect': request.META.get('HTTP_REFERER'),
            'is_staff': True,
            }),
        Participant.ROLE_STAFF
        )

def client_join_chat(request):
    return join_chat(
        request,
        dict({
                'logout_redirect': '/logged_out/',
                'unavailable_redirect': '/unavailable/',
                'is_staff': False,
            })
        )

def join_chat(request, cfg, role=Participant.ROLE_CLIENT):
    if request.COOKIES.has_key('room_token'):
        token = request.COOKIES.get('room_token')
    else:
        token = AccessToken.create(role).token

    return render_to_response(
      'rooms/join_chat.html', {
      'debug': settings.DEBUG,
      'xmpptk_config': dumps(dict({
                'muc_nick': request.user.username,
                'logout_redirect': request.META.get('HTTP_REFERER'),
                'bot_jid': '%s@%s' % (settings.BOT['connection']['username'], settings.BOT['connection']['domain']),
                'bot_nick': settings.BOT['muc']['nick'],
                'static_url': settings.STATIC_URL,
                'is_one2one': True,
                'is_staff': True,
                'token': token,
      }.items() + settings.CHAT.items() + cfg.items()), indent=2)
    })
