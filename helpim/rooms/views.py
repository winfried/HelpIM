from django.http import HttpResponse
from helpim.rooms.models import One2OneRoom
from django.shortcuts import get_object_or_404, redirect
from django.utils.simplejson import dumps
from django.db import transaction

@transaction.commit_on_success
def staff_join_chat(request, room_pk=None):
    if room_pk:
      try:
        room = One2OneRoom.objects.get(pk=room_pk, status__exact='staffWaiting')
      except One2OneRoom.DoesNotExist:
        # Room is not available to join anymore, choose a new one
        return redirect('/admin/rooms/one2oneroom/')

    else:
      try:
        room = One2OneRoom.objects.filter(status__exact='staffWaiting')[:1][0]
      except IndexError:
        # bot should always keep a few rooms available
        # XXX raise ? This is a error 500 IMHO
        return redirect('/admin/rooms/one2oneroom/')

    assert room.status == 'staffWaiting'

    # XXX does the bot also change this status ? Joining should be atomic so a
    # room is not entered by two care workers
    room.status = 'staffWaitingForInvitee'
    room.save()

    html = (
      "<html><body>Opening chat.." +
      "<pre>var xmpptk_config = %(xmpptk_config)s</pre>" +
      "</body></html>"
    ) % {
      'xmpptk_config': dumps({
        'jid': room.jid,
        'password': room.password,
      })
    }
    return HttpResponse(html)
