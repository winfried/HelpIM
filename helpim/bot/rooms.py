"""Clases for handling the chatrooms connected to one site"""
# note: these classes don't use the sqlalchemy ORM, because it caches.
# the roomstatusses need to be atomic and instantanious

import sqlalchemy
import datetime

class Site:
    def __init__(self, name):
        self.name = name
        self.rooms = Rooms()
        self.groupRooms = GroupRooms()

def getSites():
    return {'helpim': Site('helpim')}

class StatusError(Exception):
    pass

class RoomBase():

    def _createRoom(self, jid, password):
        if not jid:
            raise TypeError("Need a jid to create a new room object")
        self.jid = jid
        self.password = password
        stmt = self.table.insert().values(jid=jid,
                                    password=password,
                                    status='available')
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        # get id of this room
        stmt = self.table.select(self.table.c.jid==jid)
        rp = self.execute(stmt)
        result=rp.fetchone()
        self.id = result[0]
        rp.close()
        self.connection.close()

    def getStatus(self):
        """Returns the current status of the room."""
        stmt = sqlalchemy.select([self.table.c.status],
                                 self.table.c.jid==self.jid)
        rp = self.execute(stmt)
        result = rp.fetchone()[0]
        rp.close()
        self.connection.close()
        return result

    def setStatus(self, status):
        """Sets the status of the room to 'status'. 'Status' must be a
           valid status or a StatusError is raised."""
        if status not in self.validStatusses:
            raise StatusError("Programming error: invalid room status '%s'", status)
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            status=status,
            status_timestamp=datetime.datetime.now())
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()

    def setChatId(self, chatId):
        """Sets the chatId of the room to 'chatId'."""
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            chat_id=chatId)
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        self.chat_id = chatId

    def getCleanExit(self):
        """Returns a boolean. True if the webapp detected the room had
           a clean exit."""
        stmt = sqlalchemy.select([self.table.c.web_clean_exit],
                                 self.table.c.jid==self.jid)
        rp = self.execute(stmt)
        result = rp.fetchone()[0]
        rp.close()
        self.connection.close()
        return result

    def setCleanExit(self):
        """Sets the 'clean exit flag' of this room in the database.
           May only be used by the webapp."""
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            web_clean_exit=True)
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()

    def setPassword(self, password):
        """Sets the password of the room."""
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            password=password)
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        self.password = password

    def destroyed(self):
        """To be called after the room is destroyed at the jabber-server."""
        self.setStatus("destroyed")


class One2OneRoom(RoomBase):
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

    validStatusses = (
        "available",
        "availableForInvitation",
        "staffWaiting",
        "staffWaitingForInvitee",
        "chatting",
        "closingChat",
        "toDestroy",
        "destroyed",
        "lost",
        "abandoned"
        )

    def __init__(self, metadata, engine, jid=None, password=None, clientId=None, roomId=None, load=False):
        """Create an empty One2OneRoom object or loads an existing room

           Keyword arguments:
           metadata -- sqlalchemy.metadata  Metadata of the database to use.
           jid -- string  Jid of room to load or to create.
                  Oblidged if the room is not loaded from database.
           password -- string  Password of the room to load or create.
           clientId -- string  id of the client in the room to load or create.
           load -- Boolean  If true, a room will be loaded from database
                   When load is true, a jid or password needs to be given to find
                   the room.
           """
        self.type="One2OneRoom"
        self.metadata = metadata
        self.engine = engine
        self.table = metadata.tables['One2OneRoom']
        if load:
            if not (jid or password or clientId or roomId):
                raise TypeError("Need a jid, a client id or a password")
            if jid:
                stmt = self.table.select(self.table.c.jid==jid)
            elif clientId:
                stmt = self.table.select(self.table.c.client_id==clientId)
            elif roomId:
                stmt = self.table.select(self.table.c.id==roomId)
            else:
                stmt = self.table.select(self.table.c.password==password)
            rp = self.execute(stmt)
            result=rp.fetchone()
            rp.close()
            self.connection.close()
            if result == None and jid:
                raise KeyError("Jid not found in database")
            elif result == None and clientId:
                raise KeyError("Client id not found in database")
            elif result == None and password:
                raise KeyError("Password not found in database")
            elif result == None and roomId:
                raise KeyError("roomId not found in database")
            self.id = result[0]
            self.jid = result[1]
            self.password = result[2]
            self.chat_id = result[4]
            self.staff_id = result[5]
            self.client_id = result[6]
            self.staff_nick = result[7]
            self.client_nick = result[8]
        else:
            self._createRoom(jid, password)

    def setClientId(self, clientId):
        """Sets the client_id of the room to 'clientId'."""
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            client_id=clientId)
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        self.client_id = clientId

    def setStaffNick(self, staffNick):
        """Sets the nick of the staff to 'staffNick'."""
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            staff_nick=staffNick)
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        self.staff_nick = staffNick

    def setClientNick(self, clientNick):
        """Sets the nick of the client to 'clientNick'."""
        stmt = self.table.update().where(self.table.c.jid==self.jid).values(
            client_nick=clientNick)
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        self.client_nick = clientNick

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


class GroupRoom(RoomBase):
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

    validStatusses = (
        "available",
        "chatting",
        "toDestroy",
        "destroyed",
        "abandoned"
        )

    def __init__(self, metadata, engine, jid=None, password=None, roomId=None, load=False):
        self.type = "GroupRoom"
        self.metadata = metadata
        self.engine = engine
        self.table = metadata.tables['GroupRoom']
        if load:
            if not (jid or password or roomId):
                raise TypeError("Need a jid, a room id or a password")
            if jid:
                stmt = self.table.select(self.table.c.jid==jid)
            elif roomId:
                stmt = self.table.select(self.table.c.id==roomId)
            else:
                stmt = self.table.select(self.table.c.password==password)
            rp = self.execute(stmt)
            result=rp.fetchone()
            rp.close()
            self.connection.close()
            if result == None and jid:
                raise KeyError("Jid not found in database")
            elif result == None and password:
                raise KeyError("Password not found in database")
            elif result == None and roomId:
                raise KeyError("roomId not found in database")
            self.id = result[0]
            self.jid = result[1]
            self.password = result[2]
            self.chat_id = result[4]
        else:
            self._createRoom(jid, password)

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


class Rooms():
    """Container for all chatrooms of a site"""

    def newRoom(self, jid, password):
        """Adds a new room to the rooms, returns the new room object"""
        return One2OneRoom(self.metadata, self.engine, jid, password)

    def getToDestroy(self):
        """Returns a list with all rooms with status 'toDestroy'"""
        return self.getByStatus("toDestroy")

    def getAvailable(self):
        """Returns a list with all rooms with status 'available'"""
        return self.getByStatus("available")

    def getAvailableForInvitation(self):
        """Returns a list with all rooms with status 'availableForInvitation'"""
        return self.getByStatus("availableForInvitation")

    def getChatting(self):
        """Returns a list with all rooms with status 'chatting'"""
        return self.getByStatus("chatting")

    def getAbandoned(self):
        """Returns a list with all rooms with status 'abandoned'"""
        return self.getByStatus("abandoned")

    def getStaffWaiting(self):
        """Returns a list with all rooms with status 'staffWaiting'"""
        return self.getByStatus("staffWaiting")

    def getStaffWaitingForInvitee(self):
        """Returns a list with all rooms with status 'staffWaitingForInvitee'"""
        return self.getByStatus("staffWaitingForInvitee")

    def __getRoomsByJids(self, jids):
        """Private function to convert a list from a resultproxy
           fetchaall() to a list of rooms."""
        rooms = []
        for jid in jids:
            rooms.append(One2OneRoom(self.metadata,
                                     self.engine,
                                     jid=jid[0],
                                     load=True))
        return rooms

    def getAll(self):
        """Returns a list with all room-objects"""
        stmt = sqlalchemy.select([self.table.c.jid])
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getByStatus(self, status):
        """Returns a list with room-objects with status 'status'

           Keyword arguments:
           status -- string, the status to select the rooms on
           """
        stmt = sqlalchemy.select([self.table.c.jid],
                                 self.table.c.status==status)
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getStatusById(self, roomId):
        """Returns a string with the status of the room with the given
           id.
           Keyword arguments:
           id -- int, the id of the room the status of is requested
           """
        stmt = sqlalchemy.select([self.table.c.status],
                                 self.table.c.id==roomId)
        rp = self.execute(stmt)
        status = rp.fetchone()
        if status:
            return status[0]
        else:
            return None

    def getTimedOut(self, status, timeout):
        """Returns a list with room-objects with status 'status' that
           have that status longer then 'timeout'

           Keyword arguments:
           status -- string, the status to select the rooms on
           timeout -- timeout in seconds
           """
        cutOffTime=datetime.datetime.now()-datetime.timedelta(seconds=timeout)
        stmt = sqlalchemy.select([self.table.c.jid],
                                 (self.table.c.status==status) &
                                 (self.table.c.status_timestamp<=cutOffTime))
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getHangingStaffStart(self, timeout):
        """Returns a list with room-objects with status 'status' that
           have that status longer then 'timeout'

           Keyword arguments:
           status -- string, the status to select the rooms on
           timeout -- timeout in seconds
           """
        cutOffTime=datetime.datetime.now()-datetime.timedelta(seconds=timeout)
        stmt = sqlalchemy.select([self.table.c.jid],
                                 ((self.table.c.status=='available')
                                  | (self.table.c.status=='availableForInvitation')) &
                                 (self.table.c.modified_timestamp<=cutOffTime) &
                                 (self.table.c.staff_id!=None))
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getNotDestroyed(self):
        """Returns a list with room-objects that are not destroyed."""
        rooms = []
        stmt = sqlalchemy.select([self.table.c.jid],
                                 self.table.c.status!='destroyed')
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getByJid(self, jid):
        """Returns the room-objects with given jid

           Keyword arguments:
           jid -- string, jid to select the rooms on
           """
        return One2OneRoom(self.metadata, self.engine, jid=jid, load=True)

    def getByPassword(self, password):
        """Returns the room-objects with given password

           Keyword arguments:
           password -- string, password to select the room on
           """
        return One2OneRoom(self.metadata, self.engine, password=password, load=True)

    def getByClientId(self, clientId):
        """Returns the room-objects with given clientId

           Keyword arguments:
           clientId -- string, client id to select the room on
           """
        return One2OneRoom(self.metadata, self.engine, clientId=clientId, load=True)

    def admitStaff(self, staff_id):
        """Tries to bind a staff to an available room. Returns False if
           it failed, returns the room object it binded to if succeeded

           Keyword arguments:
           staff_id -- id of the staff that should be bound to a room
           """
        connection = self.engine.connect()
        trans = connection.begin()
        # use for_update = True to lock the record until it is committed
        stmt = sqlalchemy.select([self.table.c.jid],
                              (self.table.c.staff_id==None) &
                              (self.table.c.status=='available'),
                              limit=1,
                              for_update=True)
        rp = connection.execute(stmt)
        jid = rp.fetchall()
        rp.close()
        if not jid:
            trans.commit()
            connection.close()
            return False
        jid = jid[0][0]
        stmt = self.table.update().where(self.table.c.jid==jid).values(staff_id=staff_id)
        rp = connection.execute(stmt)
        if rp.rowcount == 0:
            rp.close()
            trans.commit()
            connection.close()
            return False
        rp.close()
        trans.commit()
        connection.close()
        return One2OneRoom(self.metadata, self.engine, jid=jid, load=True)

    def admitStaffInvitation(self, staff_id):
        """Tries to bind a staff to an available room. Returns False if
           it failed, returns the room object it binded to if succeeded

           Keyword arguments:
           staff_id -- id of the staff that should be bound to a room
           """
        connection = self.engine.connect()
        trans = connection.begin()
        # use for_update = True to lock the record until it is committed
        stmt = sqlalchemy.select([self.table.c.jid],
                              (self.table.c.staff_id==None) &
                              (self.table.c.status=='available'),
                              limit=1,
                              for_update=True)
        rp = connection.execute(stmt)
        jid = rp.fetchall()
        rp.close()
        if not jid:
            trans.commit()
            connection.close()
            return False
        jid = jid[0][0]
        stmt = self.table.update().where(self.table.c.jid==jid).values(staff_id=staff_id)
        rp = connection.execute(stmt)
        if rp.rowcount == 0:
            rp.close()
            trans.commit()
            connection.close()
            return False
        rp.close()
        trans.commit()
        connection.close()
        room = One2OneRoom(self.metadata, self.engine, jid=jid, load=True)
        room.setStatus('availableForInvitation')
        return room

    def admitClient(self, client_id):
        """Tries to bind a client to a room with staff waiting. Returns
           False if it failed, returns the room object it binded to if
           succeeded.

           Keyword arguments:
           client_id -- id of the client that should be bound to a room
           """
        connection = self.engine.connect()
        trans = connection.begin()
        # use for_update = True to lock the record until it is committed
        stmt = sqlalchemy.select([self.table.c.jid],
                              (self.table.c.client_id==None) &
                              (self.table.c.status=='staffWaiting'),
                              limit=1,
                              for_update=True)
        rp = connection.execute(stmt)
        jid = rp.fetchall()
        rp.close()
        if not jid:
            trans.commit()
            connection.close()
            return False
        jid = jid[0][0]
        stmt = self.table.update().where(self.table.c.jid==jid).values(client_id=client_id)
        rp = self.execute(stmt)
        if rp.rowcount == 0:
            rp.close()
            trans.commit()
            connection.close()
            return False
        rp.close()
        trans.commit()
        connection.close()
        return One2OneRoom(self.metadata, self.engine, jid=jid, load=True)

    def admintClientInvitation(self, roomId, clientId):
        """Tries to bind a client to the room where the staff with the given
           id is waiting. Returns false if the room is not available, returns
           the room object if succeeded.

           Keyword arguments:
           staff_id -- id of the staff the client should be connected to
           client_id -- id of the client that should be bound to the staff
           """
        room = One2OneRoom(self.metadata, self.engine, roomId=roomId, load=True)
        if not room.getStatus() == "staffWaitingForInvitee":
            raise Exception("Attempt to enter room where inviter should be waiting, but room has status: " + room.getStatus())
        room.setClientId(clientId)
        return room

    def deleteClosed(self):
        """Deletes records with the status 'destroyed'"""
        stmt = sqlalchemy.delete(self.table, (self.table.c.status=='destroyed'))
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        return

class GroupRooms():
    """Container for all chatrooms of a site"""

    def newRoom(self, jid, password):
        """Adds a new room to the rooms, returns the new room object"""
        return GroupRoom(self.metadata, self.engine, jid, password)

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

    def __getRoomsByJids(self, jids):
        """Private function to convert a list from a resultproxy
           fetchaall() to a list of rooms."""
        rooms = []
        for jid in jids:
            rooms.append(GroupRoom(self.metadata,
                                     self.engine,
                                     jid=jid[0],
                                     load=True))
        return rooms

    def getAll(self):
        """Returns a list with all room-objects"""
        stmt = sqlalchemy.select([self.table.c.jid])
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getByStatus(self, status):
        """Returns a list with room-objects with status 'status'

           Keyword arguments:
           status -- string, the status to select the rooms on
           """
        stmt = sqlalchemy.select([self.table.c.jid],
                                 self.table.c.status==status)
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getStatusById(self, roomId):
        """Returns a string with the status of the room with the given
           id.
           Keyword arguments:
           id -- int, the id of the room the status of is requested
           """
        stmt = sqlalchemy.select([self.table.c.status],
                                 self.table.c.id==roomId)
        rp = self.execute(stmt)
        status = rp.fetchone()
        if status:
            return status[0]
        else:
            return None

    def getTimedOut(self, status, timeout):
        """Returns a list with room-objects with status 'status' that
           have that status longer then 'timeout'

           Keyword arguments:
           status -- string, the status to select the rooms on
           timeout -- timeout in seconds
           """
        cutOffTime=datetime.datetime.now()-datetime.timedelta(seconds=timeout)
        stmt = sqlalchemy.select([self.table.c.jid],
                                 (self.table.c.status==status) &
                                 (self.table.c.status_timestamp<=cutOffTime))
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getNotDestroyed(self):
        """Returns a list with room-objects that are not destroyed."""
        rooms = []
        stmt = sqlalchemy.select([self.table.c.jid],
                                 self.table.c.status!='destroyed')
        rp = self.execute(stmt)
        jids = rp.fetchall()
        rp.close()
        self.connection.close()
        return self.__getRoomsByJids(jids)

    def getByJid(self, jid):
        """Returns the room-objects with given jid

           Keyword arguments:
           jid -- string, jid to select the rooms on
           """
        return GroupRoom(self.metadata, self.engine, jid=jid, load=True)

    def getByPassword(self, password):
        """Returns the room-objects with given password

           Keyword arguments:
           password -- string, password to select the room on
           """
        return GroupRoom(self.metadata, self.engine, password=password, load=True)

    def deleteClosed(self):
        """Deletes records with the status 'destroyed'"""
        stmt = sqlalchemy.delete(self.table, (self.table.c.status=='destroyed'))
        rp = self.execute(stmt)
        rp.close()
        self.connection.close()
        return

    def admitToGroup(self, chatId):
        """Admits a client to the group with id 'chat_id'. If no room is
           assigend to that chat, a new room is assigned to it. Returns
           False if it failed, returns the room object it binded to if
           succeeded.

           Keyword arguments:
           chat_id -- id of the chat the client should be admitted to.
           """
        chatId=int(chatId)
        connection = self.engine.connect()
        trans = connection.begin()
        # use for_update = True to lock the record until it is committed
        stmt = sqlalchemy.select([self.table.c.jid]).where(self.table.c.chat_id==sqlalchemy.sql.bindparam("Cid"))
        rp = connection.execute(stmt, Cid=chatId)
        jid = rp.fetchall()
        rp.close()
        if jid:
            # room was already assigned, extract the jid, we can move on to returning the room
            jid = jid[0][0]
        else:
            # assign a room
            # use for_update = True to lock the record until it is committed
            stmt = sqlalchemy.select([self.table.c.jid],
                                    (self.table.c.chat_id==None) &
                                    (self.table.c.status=='available'),
                                    limit=1,
                                    for_update=True)
            rp = connection.execute(stmt)
            jid = rp.fetchall()
            rp.close()
            if jid:
                # Great, we found an empty room
                jid = jid[0][0]
            else:
                # Failure, probably the bot not running
                trans.commit()
                connection.close()
                return False
            # set the chat_id
            stmt = self.table.update().where(self.table.c.jid==jid).values(chat_id=chatId)
            rp = connection.execute(stmt)
            rp.close()
        trans.commit()
        connection.close()
        return GroupRoom(self.metadata, self.engine, jid=jid, load=True)
