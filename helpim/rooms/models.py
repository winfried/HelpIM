from django.db import models

from helpim.conversations.models import Chat, Participant
from django.utils.translation import ugettext as _

class StatusError(Exception):
    """ thrown when rooms status is set to a bad value
    this does not refer to a value that's not defined
    this refers to a value that's not intended by the defined protocol flow """
    pass

class Room(models.Model):
    """ abstract base class for all kind of rooms """
    STATUS_CHOICES = () # this must be overriden by inheriting class

    jid = models.CharField(max_length=255,
                           unique=True)
    status = models.CharField(max_length=32,
                              choices=STATUS_CHOICES)
    password = models.CharField(max_length=64)
    chat = models.ForeignKey(Chat)
    web_clean_exit = models.BooleanField()
    status_timestamp = models.DateTimeField()
    modified_timestamp = models.DateTimeField()

    class Meta:
        abstract = True

    def getStatus(self):
        return self.status

    def setStatus(self, status):
        self.status = status
        self.save()

    def setChatId(slef, chatId):
        chat = Chat.objects.get(pk=chatId)
        self.chat = chat
        self.save()

    def getCleanExit(self):
        return selt.web_clean_exit

    def setCleanExit(self):
        self.web_clean_exit = True
        self.save()

    def setPassword(self, password):
        self.password = password
        self.save()

    def destroyed(self):
        self.setStatus('destroyed')

class One2OneRoom(Room):
    """Chatroom for having one-to-one chats.
       When created, it is just an empty object with the status:
       'available'. The room object must be created when the room is
       actually created on the jabber-server.

       A full list of possible statusses of a one-to-one room:

       available    Jid is known, room is created at jabber-server.
       availableForInvitation
                    Jid is known, room is created at the jabber-server
                    and the room is assigned for a chat by invitation.
       staffWaiting A staffmember has entered the room and is waiting
                    for a client to chat with.
       staffWatingForInvitee
                    A staffmember has entered the room and is waiting
                    for the client invited for the chat to enter.
       chatting     Both a staffmember and a client are present in the
                    room, hopefully they are chatting.
       closingChat  The staffmembor OR the client is still present, but
                    one of them initiated the closing of the chat. The
                    remaining participant(s) should leave or be kicked
                    if the participant doesn't leave before te time-out.
       toDestroy    There has been a chat and both partitipants have left.
                    There is no need anymore to keep the room at the
                    jabber-server.
       destroyed    The room is destroyed at the jabber-server.
       lost         During a chat one of the participants disapeared
                    without confirming an end of the chat.
       abandoned    During a chat both the client and the staffmember
                    disapeared without confirming an end of the chat.
                    If none of them return before the timeout, the room
                    must be destroyed.
       """

    STATUS_CHOICES = (
        ('available', _('Available')),
        ('availableForInvitation', _('Available for Invitation')),
        ('staffWaiting', _('Staff Waiting')),
        ('staffWaitingForInvitee', _('Staff Waiting for Invitee')),
        ('chatting', _('Chatting')),
        ('closingChat', _('Closing Chat')),
        ('toDestroy', _('To Destroy')),
        ('destroyed', _('Destroyed')),
        ('lost', _('Lost')),
        ('abandoned', _('Abandoned')),
        )

    staff = models.ForeignKey(Participant, related_name='+')
    staff_nick = models.CharField(max_length=64)
    client = models.ForeignKey(Participant, related_name='+')
    client_nick = models.CharField(max_length=64)

    def setClientId(self, clientId):
        client = Participant.objects.get(pk=clientId)
        self.client = client
        self.save()

    def setStaffNick(self, nick):
        self.staff_nick = nick
        self.save()

    def setClientNick(self, nick):
        self.client_nick = nick
        self.save()

    def staffJoined(self):
        """To be called after the staffmember has joined
        the room at the jabber-server.
        """
        if self.getStatus() == "available":
            self.setStatus("staffWaiting")
        elif self.getStatus() == "availableForInvitation":
            self.setStatus("staffWaitingForInvitee")
        else:
            raise StatusError("staff joining room while not room status is not 'available' or 'availableForInvitation'")

    def clientJoined(self):
        """To be called after a client has joined
           the room at the jabber-server.
           """
        if self.getStatus() in ("staffWaiting", "staffWaitingForInvitee"):
            self.setStatus("chatting")
        else:
            raise StatusError("client joining room while not room status is not 'staffWaiting' or 'staffWaitingForInvitee'")

    def userLeftDirty(self):
        """To be called when a participant (either client or staff) has left the chat."""
        status = self.getStatus()
        if status == 'lost':
            self.setStatus('abandoned')
        elif status == 'chatting':
            self.setStatus('lost')
        elif status in ('staffWaiting', 'staffWaitingForInvitee', 'closingChat'):
            self.setStatus('toDestroy')
        else:
            raise StatusError("Participant left dirty while status is '%s'." % status)

    def userLeftClean(self):
        """To be called when a participant (either client or staff) has left the chat."""
        status = self.getStatus()
        if status in ('lost', 'staffWaiting', 'staffWaitingForInvitee', 'closingChat'):
            self.setStatus('toDestroy')
        elif status == 'chatting':
            self.setStatus('closingChat')
        else:
            raise StatusError("Participant left clean while status is '%s'." % status)

class GroupRoom(Room):
    """Chatroom for having groupchats.
       When created, it is just an empty object with the status:
       'available'. The room object must be created when the room is
       actually created on the jabber-server.

       A full list of possible statusses of a one-to-one room:

       available    Jid is known, room is created at jabber-server.
       chatting     At least one participant is present.
       toDestroy    There has been a groupchat, all partitipants have
                    left and the last participent has left cleanly..
                    There is no need anymore to keep the room at the
                    jabber-server.
       destroyed    The room is destroyed at the jabber-server.
       abandoned    There has been a groupchat, all partitipants have
                    left and the last participent has left dirty.
                    If none of the participants return before the
                    timeout, the room must be destroyed.
       """

    STATUS_CHOICES = (
        ('available', _('Available')),
        ('chatting', _('Chatting')),
        ('toDestroy', _('To Destroy')),
        ('destroyed', _('Destroyed')),
        ('abandoned', _('Abandoned')),
        )

    status = models.CharField(max_length=32,
                              choices=STATUS_CHOICES)

    def userJoined(self):
        """To be called after a client has joined
           the room at the jabber-server.
           """
        status = self.getStatus()
        if status in ("available", "abandoned"):
            self.setStatus("chatting")
        elif status == "chatting":
            pass
        else:
            raise StatusError("client joining room while not room status is not 'available' or 'chatting'")

    # ToDo: these functions need to be adapted!!!!!!!

    def lastUserLeftDirty(self):
        """To be called when the last participant has left the chat dirty."""
        if not self.getStatus() == "chatting":
            raise StatusError("Participant left dirty while status was not chatting")
        self.setStatus('abandoned')

    def lastUserLeftClean(self):
        """To be called when the last participant has left the chat clean."""
        if not self.getStatus() == "chatting":
            raise StatusError("Participant left clean while status was not chatting")
        self.setStatus('toDestroy')
