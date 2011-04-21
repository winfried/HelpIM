import datetime

from django.db import models
from django.utils.translation import ugettext as _

from helpim.conversations.models import Chat, Participant

class Site:
    def __init__(self, name):
        self.name = name
        """ [FIXME] will it blend? """
        self.rooms = One2OneRoom.objects
        self.groupRooms = GroupRoom.objects

def getSites():
    """ this is a fake sites dict as we're not using real sites right now """
    return {'helpim': Site('helpim')}

class RoomManager(models.Manager):
    def newRoom(self, jid, password):
        """Adds a new room to the rooms, returns the new room object"""
        room = self.model(jid=jid, password=password)
        room.save()
        return room
    
    def getToDestroy(self):
        """Returns a list with all rooms with status 'toDestroy'"""
        return self.getByStatus("toDestroy")

    def getAvailable(self):
        """Returns a list with all rooms with status 'available'"""
        return self.getByStatus("available")

    def getChatting(self):
        """Returns a list with all rooms with status 'chatting'"""
        return self.getByStatus("chatting")

    def getAbandoned(self):
        """Returns a list with all rooms with status 'abandoned'"""
        return self.getByStatus("abandoned")

    def getAll(self):
        """Returns a list with all room-objects"""
        return list(self.all())

    def getByStatus(self, status):
        """Returns a list with room-objects with status 'status'

           Keyword arguments:
           status -- string, the status to select the rooms on
           """
        return list(self.filter(status=status))

    def getStatusById(self, roomId):
        """Returns a string with the status of the room with the given
           id.
           Keyword arguments:
           id -- int, the id of the room the status of is requested
           """
        return self.get(pk=roomId).status

    def getTimedOut(self, status, timeout):
        """Returns a list with room-objects with status 'status' that
           have that status longer then 'timeout'

           Keyword arguments:
           status -- string, the status to select the rooms on
           timeout -- timeout in seconds
           """
        cutOffTime=datetime.datetime.now()-datetime.timedelta(seconds=timeout)
        return list(self.filter(status=status).filter(status_timestamp__lte=cutOffTime))

    def getNotDestroyed(self):
        """Returns a list with room-objects that are not destroyed."""
        return list(self.exclude(status='destroyed'))

    def getByJid(self, jid):
        """Returns the room-objects with given jid

           Keyword arguments:
           jid -- string, jid to select the rooms on
           """
        return self.get(jid=jid)

    def getByPassword(self, password):
        """Returns the room-objects with given password

           Keyword arguments:
           password -- string, password to select the room on
           """
        return self.get(password=password)

    def deleteClosed(self):
        """Deletes records with the status 'destroyed'"""
        self.filter(status='destroyed').delete()

class One2OneRoomManager(RoomManager):
    def getAvailableForInvitation(self):
        """Returns a list with all rooms with status 'availableForInvitation'"""
        return self.getByStatus("availableForInvitation")

    def getStaffWaiting(self):
        """Returns a list with all rooms with status 'staffWaiting'"""
        return self.getByStatus("staffWaiting")

    def getStaffWaitingForInvitee(self):
        """Returns a list with all rooms with status 'staffWaitingForInvitee'"""
        return self.getByStatus("staffWaitingForInvitee")

    def getHangingStaffStart(self, timeout):
        """Returns a list with room-objects with status 'status' that
           have that status longer then 'timeout'

           Keyword arguments:
           status -- string, the status to select the rooms on
           timeout -- timeout in seconds
           """
        cutOffTime=datetime.datetime.now()-datetime.timedelta(seconds=timeout)
        return list(
            self.filter(
                models.Q(status='available') | models.Q(status='availableForInvitation'),
                modified_timestamp__lte=cutOffTime).exclude(staff=None))

    def getByClientId(self, clientId):
        """Returns the room-objects with given clientId

           Keyword arguments:
           clientId -- string, client id to select the room on
           """
        client = Participant.objects.get(pk=clientId)
        return self.get(client=client)

    def admitStaff(self, staff_id):
        """Tries to bind a staff to an available room. Returns False if
           it failed, returns the room object it binded to if succeeded

           Keyword arguments:
           staff_id -- id of the staff that should be bound to a room
           """
        pass

    def admitStaffInvitation(self, staff_id):
        """Tries to bind a staff to an available room. Returns False if
           it failed, returns the room object it binded to if succeeded

           Keyword arguments:
           staff_id -- id of the staff that should be bound to a room
           """
        pass

    def admitClient(self, client_id):
        """Tries to bind a client to a room with staff waiting. Returns
           False if it failed, returns the room object it binded to if
           succeeded.

           Keyword arguments:
           client_id -- id of the client that should be bound to a room
           """
        pass

    def admintClientInvitation(self, roomId, clientId):
        """Tries to bind a client to the room where the staff with the given
           id is waiting. Returns false if the room is not available, returns
           the room object if succeeded.

           Keyword arguments:
           staff_id -- id of the staff the client should be connected to
           client_id -- id of the client that should be bound to the staff
           """
        pass

class GroupRoomManager(RoomManager):
    def admitToGroup(self, chatId):
        """Admits a client to the group with id 'chat_id'. If no room is
        assigend to that chat, a new room is assigned to it. Returns
        False if it failed, returns the room object it binded to if
        succeeded.
           
        Keyword arguments:
        chat_id -- id of the chat the client should be admitted to.
        """
        pass

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

    objects = One2OneRoomManager()

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

    objects = GroupRoomManager()

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
