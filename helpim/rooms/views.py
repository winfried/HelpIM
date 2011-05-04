from django.http import HttpResponse
from helpim.rooms.models import One2OneRoom
from django.shortcuts import get_object_or_404, redirect
from django.utils.simplejson import dumps
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render_to_response

@transaction.commit_on_success
@login_required
def staff_join_chat(request, room_pk=None):
    if room_pk:
      try:
        room = One2OneRoom.objects.get(pk=room_pk, status__exact='available')
      except One2OneRoom.DoesNotExist:
        # Room is not available to join anymore, choose a new one
        return redirect('/admin/rooms/one2oneroom/')

    else:
      try:
        room = One2OneRoom.objects.filter(status__exact='available')[:1][0]
      except IndexError:
        # bot should always keep a few rooms available
        # XXX raise ? This is a error 500 IMHO
        return redirect('/admin/rooms/one2oneroom/')

    assert room.status == 'available'

    # XXX does the bot also change this status ? Joining should be atomic so a
    # room is not entered by two care workers
#    room.status = 'staffWaiting'
#    room.save()

    return render_to_response(
      'rooms/staff_join_chat.html', {
      'debug': settings.DEBUG,
      'xmpptk_config': dumps({
          'httpbase': "/http-bind/",
          'authtype': "saslanon",
          'domain': settings.BOT['connection']['domain'],
          'muc_service': room.getRoomService(),
          'muc_room': room.getRoomId(),
          'muc_password': room.password,
          'muc_nick': request.user.username,
          'mode': 'light',
          'logout_redirect': request.META.get('HTTP_REFERER'),
          'bot_nick': settings.BOT['muc']['nick'],
      }, indent=2)
    })


