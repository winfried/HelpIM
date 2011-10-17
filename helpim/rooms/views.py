from hashlib import md5

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.simplejson import dumps
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render_to_response
from django.forms import Form, CharField
from django.core.context_processors import csrf

from helpim.rooms.models import AccessToken, Participant, IPBlockedException

@login_required
def staff_join_chat(request, room_pk=None):
    return join_chat(
        request,
        dict({
            'muc_nick': request.user.username,
            'logout_redirect': request.META.get('HTTP_REFERER') or request.build_absolute_uri('/admin/'),
            'conversation_redirect': request.build_absolute_uri('/admin/conversations/conversation/'),
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

def join_chat(request, cfg, role=Participant.ROLE_CLIENT):
    try:
        token = AccessToken.objects.get_or_create(token=request.COOKIES.get('room_token'), role=role, ip_hash=md5(request.META.get('REMOTE_ADDR')).hexdigest())

        return render_to_response(
            'rooms/join_chat.html', {
                'debug': settings.DEBUG,
                'is_staff': role is Participant.ROLE_STAFF,
                'is_one2one': True,
                'xmpptk_config': dumps(dict({
                            'logout_redirect': request.META.get('HTTP_REFERER'),
                            'bot_jid': '%s@%s/%s' % (settings.BOT['connection']['username'],
                                                     settings.BOT['connection']['domain'],
                                                     settings.BOT['connection']['resource']),
                            'bot_nick': settings.BOT['muc']['nick'],
                            'static_url': settings.STATIC_URL,
                            'is_staff': role is Participant.ROLE_STAFF,
                            'token': token.token,
                            }.items() + settings.CHAT.items() + cfg.items()), indent=2)
                })
    except IPBlockedException:
        return render_to_response('rooms/blocked.html')
