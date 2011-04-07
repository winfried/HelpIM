from pyxmpp.jabber.client import JabberClient
from pyxmpp.jid import JID
from pyxmpp.message import Message
from pyxmpp.presence import Presence

class Bot(JabberClient):
    def __init__(self, conf):
        self.stats = Stats()
        self.__last_room_basename = None
        self.__room_name_uniqifier = 0
        self.todo = list()
        self.__lost_connection = False
        self.conf = conf
        
        c = self.conf.connection
        self.jid = JID(c.username, c.domain, c.resource)
        self.nick = c.nick.strip()
        self.password = c.password
        self.port = int(c.port)
        self.loadSites()

    def roomCleanup(self):
        for name, site in self.sites.iteritems():
            # One2OneRooms
            for room in site.rooms.getToDestroy():
                log.info("Closing room %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for status in 'lost', 'closingChat', 'abandoned':
                for room in site.rooms.getTimedOut(status, int(self.conf.mainloop.cleanup)):
                    log.notice("Closing room %s which has timed out in '%s' status." % (room.jid, status))
                    self.closeRoom(room)
            for room in site.rooms.getHangingStaffStart(int(self.conf.mainloop.cleanup)):
                log.notice("Closing room %s which is has timed out while waiting for staff to enter room" % (room.jid))
                self.closeRoom(room)
            site.rooms.deleteClosed()
            # GroupRooms
            for room in site.groupRooms.getToDestroy():
                log.info("Closing groupRoom %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for room in site.groupRooms.getTimedOut('abandoned', int(self.conf.mainloop.cleanup)):
                log.notice("Closing groupRoom %s which has timed out in '%s' status." % (room.jid, status))
                self.closeRoom(room)
            site.groupRooms.deleteClosed()
        #DBG: self.printrooms()

    def alarmHandler(self, signum, frame):
        # Assumes only to be called for alarm signal: Ignores arguments
        self.cleanup = True

    def loadSites(self):
        self.sites = getSites()

    def run(self):
        JabberClient.__init__(self, self.jid, self.password, port=self.port, disco_name="HelpIM3 chat room manager", disco_type="bot")
        self.stats.mainloopcount = 0
        self.stats.busycount = 0
        self.stats.connectionLost = 0
        self.connect() 
        self.cleanup = False
        cleanupTimeout = int(self.conf.mainloop.cleanup)
        signal(SIGALRM, self.alarmHandler)
        alarm(cleanupTimeout)
        dbg = True #DBG
        try:
            while True:
                reconnectdelay = int(self.conf.mainloop.reconnectdelay)
                eventTimeout = float(self.conf.mainloop.timeout)
                cleanupTimeout = int(self.conf.mainloop.cleanup)
                try:
                    while self.todo:
                        callme = self.todo.pop()
                        method = callme[0]
                        args = callme[1:]
                        method(*args)
                    busy = self.stream.loop_iter(eventTimeout)
                    if not busy:
                        self.stats.busycount = 0
                        self.stream.idle()
                    else:
                        self.stats.busycount += 1
                    if self.cleanup:
                        self.roomCleanup()
                        if cleanupTimeout >= 10:
                            alarm(cleanupTimeout/10) # actual alarm timeout may be off by 10%
                        else:
                            alarm(cleanupTimeout)
                        self.cleanup = False
                        
                except (AttributeError, socket.error):
                    if not dbg:
                        dbg = True
                    else:
                        raise # DBG
                    self.__lost_connection = True
                    log.critical("Lost connection. Trying to reconnect every %d seconds" % reconnectdelay)
                    reconnectcount = 1
                    self.stats.connectionLost += 1
                    while True:
                        try:
                            sleep(reconnectdelay)
                            self.connect()
                        except socket.error:
                            reconnectcount += 1
                            log.notice("Tried to reconnect %d times. Trying again in %d seconds" % (reconnectcount, reconnectdelay))
                        else:
                            log.notice("Reconnected  after %d attempts" % reconnectcount)
                            break
            self.stats.mainloopcount += 1
            if self.stats.mainloopcount >= sys.maxint:
                self.stats.mainloopcount = 0
                self.stats.busycount = 0            
                
        except KeyboardInterrupt:
            log.notice("Keyboard interrupt. Exit...")
            self.closeRooms()
            self.disconnect()

    def session_started(self):
        JabberClient.session_started(self)
        if self.__lost_connection:
            self.__lost_connection = False
            oldroomstates = self.mucmanager.rooms.values()
            for roomstate in oldroomstates:
                roomstate.leave()
                self.mucmanager.forget(roomstate)
            self.stream.idle()
            self.todo.append((self.fillMucRoomPool,))
        else:
            error = self.set_mucRoomPoolSize(self.conf.muc.poolsize)
            if error: raise BotError(error)
            self.mucmanager = MucRoomManager(self.stream)
            self.mucmanager.set_handlers(1)
        self.todo.append((self.__rejoinRooms,))   # check DB for active room and rejoin/fix them.
        self.stream.set_message_handler("normal", self.handle_message)
        self.stream.set_presence_handler("subscribe", self.handle_presence_control)

    def getMucSettings(self, site):
        '''Return dict with global MUC-settings merged with site-specific MUC-settings'''
        if isinstance(site, str):
            sitename = site
        else:
            sitename = site.name
        settings = self.conf.muc.attr.copy()
        for siteconf in self.conf.muc:
            if siteconf.tag == "site" and siteconf.name == sitename:
                for k, v in siteconf.attr.iteritems():
                    v = v.strip()
                    if v:
                        settings[k] = v
        return settings            

    def fillMucRoomPool(self, site=None):
        '''Create MUC-rooms in the pool up to configured pool size
        
        Arguments:
        site - HelpIM Site object or string with the name of the site.
               If site is None, all pools will be filled.

        '''
        if site is None:
            # Resursively do all sites
            for name in self.sites.iterkeys():
                self.fillMucRoomPool(name)
            return
        if isinstance(site, str):
            sitename = site
        else:
            sitename = site.name
        site = self.sites[sitename]
        log.info("Refilling room pool for '%s'." % sitename)
        mucconf = self.getMucSettings(sitename)
        mucdomain = mucconf["domain"]
        poolsize = int(mucconf["poolsize"])
        # FIXME: only create rooms of the type(s) needed
        # create One2OneRooms
        nAvailable = len(site.rooms.getAvailable())
        nToCreate =  poolsize - nAvailable
        log.info("Pool size for site '%s' = %d.  Currently available rooms = %d." % (sitename, poolsize, nAvailable))
        log.info("Creating %d new rooms for site '%s'." % (nToCreate, sitename))
        for tmp in range(nToCreate):
            roomname = self.newRoomName(sitename)
            password = unicode(newHash())
            log.info("Creating MUC-room '%s@%s'." % (roomname, mucdomain))
            mucstate = self.joinMucRoom(site, JID(roomname, mucdomain), password, One2OneRoomHandler)
            if mucstate:
                mucstate.request_configuration_form()
        # create GroupRooms
        nAvailable = len(site.groupRooms.getAvailable())
        nToCreate =  poolsize - nAvailable
        log.info("Pool size for site '%s' = %d.  Currently available groupRooms = %d." % (sitename, poolsize, nAvailable))
        log.info("Creating %d new groupRooms for site '%s'." % (nToCreate, sitename))
        for tmp in range(nToCreate):
            roomname = self.newRoomName(sitename)
            password = unicode(newHash())
            log.info("Creating MUC-room for groupchat '%s@%s'." % (roomname, mucdomain))
            mucstate = self.joinMucRoom(site, JID(roomname, mucdomain), password, GroupRoomHandler)
            if mucstate:
                mucstate.request_configuration_form()

    def __rejoinRooms(self):
        '''Get all room from the database where the bot should be present as owner.
           This retakes control of the rooms that are still active according to
           that database.
           Also fixes the room statusses (where possible).
        '''
        for name, site in self.sites.iteritems():
            for room in site.rooms.getNotDestroyed():
                log.notice("Re-joining room '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, One2OneRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixroomstatus(room, mucstate)
            for room in site.groupRooms.getNotDestroyed():
                log.notice("Re-joining groupRoom '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, GroupRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixgrouproomstatus(room, mucstate)

    def fixroomstatus(self, room, mucstate): 
        # Wait until all events are processed
        # i.e. until all presence stanzas are received so we can count 
        # the number of users in the freshly re-joined rooms
        while self.stream.loop_iter(1):
            log.debug("Looping until all pending events are processed.")

        log.notice("Checking status for room '%s'." % room.jid)
        status = room.getStatus()
        log.notice("Status is '%s' for room '%s'." % (status, room.jid))
        client_id = room.client_id
        staff_id = room.staff_id
        userexited = room.getCleanExit()
        nUsers = len(mucstate.users) - 1 # -1 for not counting the bot itself
        log.info("There are %d users in '%s'." % (nUsers, room.jid))

        if status in ("available", "availableForInvitaton"):
            if staff_id:
                if client_id:
                    log.critical("BUG: a client was send to this room while status was still 'available' or 'availableForInvitation'. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
                else:
                    if nUsers >= 2:
                        log.error("BUG: two users in the room while only staff was expected. Room: '%s'." % room.jid)
                        room.setStatus("toDestroy")
                    elif nUsers == 1:
                        log.notice("Fixing status to 'staffWaiting'. Room: '%s'." % room.jid)
                        room.setStatus("staffWaiting")
                    else: # nUsers == 0
                        log.notice("Expected staff member not present anymore: to be destroyed. Room: '%s'." % (room.jid))
                        room.setStatus("toDestroy")
            else:
                if client_id:
                    log.critical("BUG: a client was send to room while no staff ever was: to be destroyed. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
                else:
                    log.info("Status is correct.")

        elif status in ("staffWaiting", "staffWaitingForInvitee"):
            if staff_id:
                if client_id:
                    if userexited:
                        if nUsers >= 2:
                            log.error("Two users in the room while at least one has exited cleanly: to be destroyed. Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                        elif nUsers == 1:
                            log.notice("Fixing status to 'closingChat'. A user has exited cleanly. Room: '%s'." % room.jid)
                            room.setStatus("closingChat")
                        else: # nUsers == 0
                            log.notice("Both users seem to have left. At least one exited cleanly: to be destroyed Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                    else:
                        if nUsers >= 2:
                            log.error("Fixing status to 'chatting'. Two users in the room now and client was send here. Room: '%s'." % room.jid)
                            room.setStatus("chatting")
                        elif nUsers == 1:
                            log.notice("Fixing status to 'lost'. One user is missing. Room: '%s'." % room.jid)
                            room.setStatus("lost")
                        else: # nUsers == 0
                            log.notice("Fixing status to 'abandoned'. Both users missing. Room: '%s'." % room.jid)
                            room.setStatus("abandoned")
                else: # no client_id
                    if nUsers >= 2:
                        log.error("BUG: two users in the room while only staff was expected. Room: '%s'." % room.jid)
                        room.setStatus("toDestroy")
                    elif nUsers == 1:
                        log.info("Status is correct.")
                    else: # nUsers == 0
                        log.notice("Expected staff member not present anymore: to be destroyed. Room: '%s'." % room.jid)
                        room.setStatus("toDestroy")
            else: # no staff_id
                log.critical("BUG: a staff member was never send here: to be destroyed. Room: '%s'." % room.jid)
                room.setStatus("toDestroy")

        elif status == "chatting":
            if staff_id:
                if client_id:
                    if userexited:
                        if nUsers >= 2:
                            log.error("Two users in the room while at least one has exited cleanly: to be destroyed. Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                        elif nUsers == 1:
                            log.info("One user left cleanly. Fixing status to 'closingChat'.")
                            room.setStatus("closingChat")
                        else: # nUsers == 0
                            log.notice("Both users seem to have left. At least one exited cleanly: to be destroyed Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                    else: # no clean exit
                        if nUsers >= 2:
                            log.info("Status is correct.")
                        elif nUsers == 1:
                            log.notice("Fixing status to 'lost'. One user is missing. Room: '%s'." % room.jid)
                            room.setStatus("lost")
                        else: # nUsers == 0
                            log.notice("Fixing status to 'abandoned'. Both users missing. Room: '%s'." % room.jid)
                            room.setStatus("abandoned")
                else: # no client_id
                    log.error("Status 'chatting' invalid since no client was ever send here. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
            else: # no staff_id
                log.error("Status 'chatting' invalid since no staff member was ever send here. Room: '%s'." % room.jid)
                room.setStatus("toDestroy")

        elif status == 'closingChat':
            if nUsers >= 2:
                log.error("Two users in room while status was already 'closingChat'. Room: '%s'." % room.jid)
                room.setStatus("toDestroy")                
            elif nUsers == 1:
                log.info("Status is correct.")
            else: # nUsers == 0
                log.notice("No user left in room. To be destroyed. Room: '%s'." % room.jid)
                room.setStatus("abandoned")

        elif status == 'toDestroy':
            if nUsers >= 1:
                log.error("Unexpected users in room: '%s'."  % room.jid)
                room.setStatus("toDestroy")                
            else: # nUsers == 0
                log.info("Status correct.")

        elif status == 'lost':
            if userexited:
                if nUsers >= 2:
                    log.error("Unexpected user in room: '%s'."  % room.jid)
                    room.setStatus("toDestroy")
                elif nUsers == 1:
                    log.notice("Only one user in room. Closing this chat. Room: '%s'." % room.jid)
                    room.setStatus("closingChat")
                else: # nUsers == 0
                    log.notice("No user has returned. To be destroyed. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
            else:
                if nUsers >= 2:
                    log.info("Both user returned to room. Fixing status to 'chatting'. Room: '%s'."  % room.jid)
                    room.setStatus("chatting")
                elif nUsers == 1:
                    log.notice("Status is correct.")
                    room.setStatus("lost")
                else: # nUsers == 0
                    log.notice("No user has returned. Fixing status to 'abandoned'. Room: '%s'." % room.jid)
                    room.setStatus("abandoned")

        elif status == 'abandoned':
            if userexited:
                if nUsers >= 2:
                    log.error("Unexpected users in room: '%s'."  % room.jid)
                    room.setStatus("toDestroy")
                elif nUsers == 1:
                    log.notice("Only one user returned. Closing this chat. Room: '%s'." % room.jid)
                    room.setStatus("closingChat")
                else: # nUsers == 0
                    log.notice("No user has returned. To be destroyed. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
            else:
                if nUsers >= 2:
                    log.info("Both users returned to room. Fixing status to 'chatting'. Room: '%s'."  % room.jid)
                    room.setStatus("chatting")
                elif nUsers == 1:
                    log.notice("One user has returned to room. Fixing status to 'lost'. Room: '%s'."  % room.jid)
                    room.setStatus("lost")
                else: # nUsers == 0
                    log.notice("Status is correct.")
        # Finished fixing, set rejoinCount to None
        room.rejoinCount = None


    def fixgrouproomstatus(self, room, mucstate): 
        # Wait until all events are processed
        # i.e. until all presence stanzas are received so we can count 
        # the number of users in the freshly re-joined rooms
        while self.stream.loop_iter(1):
            log.debug("Looping until all pending events are processed.")

        log.notice("Checking status for group room '%s'." % room.jid)
        status = room.getStatus()
        log.notice("Status is '%s' for group room '%s'." % (status, room.jid))
        userexited = room.getCleanExit()
        chat_id = room.chat_id
        nUsers = len(mucstate.users) - 1 # -1 for not counting the bot itself
        log.info("There are %d users in '%s'." % (nUsers, room.jid))

        if status in ("available"):
            if chat_id: # room has been assigned to a chat in meanwhile
                if nUsers >= 1:
                    log.notice("Fixing status to 'chatting'. GroupRoom: '%s'." % room.jid)
                    room.setStatus("chatting")
                else: # nUsers == 0
                    log.notice("Expected users not present: mark as abandoned. GroupRoom: '%s'." % room.jid)
                    room.setStatus("abandoned")

        elif status == "chatting":
            if chat_id:
                if nUsers >= 1:
                    log.info("Status is correct.")
                else: # nUsers == 0
                    log.notice("Fixing status to 'abandoned'. All users missing. GroupRoom: '%s'." % room.jid)
                    room.setStatus("abandoned")
            else: # no chat_id
                log.error("Status 'chatting' invalid since no chat has been assigned. GroupRoom: '%s'." % room.jid)
                room.setStatus("toDestroy")

        elif status == 'abandoned':
                if nUsers >= 1:
                    log.info("User(s) returned to group room. Fixing status to 'chatting'. GroupRoom: '%s'."  % room.jid)
                    room.setStatus("chatting")
                else: # nUsers == 0
                    log.notice("Status is correct.")
        # Finished fixing, set rejoinCount to None
        room.rejoinCount = None


    def joinMucRoom(self, site, jid, password, handlerClass, rejoining=False):
        mucconf = self.getMucSettings(site.name)
        nick = mucconf["nick"].strip() or self.nick
        muchandler = handlerClass(self, site, mucconf, nick, password, rejoining)
        log.debug("MUC-room setting: history_maxchars=%s,  history_stanzas=%s, history_seconds=%s" % (
                mucconf["history_maxchars"],
                mucconf["history_maxstanzas"],
                mucconf["history_seconds"]
                ))
        try:
            mucstate = self.mucmanager.join(jid, nick, muchandler, password,
                                            mucconf["history_maxchars"],
                                            mucconf["history_maxstanzas"],
                                            mucconf["history_seconds"]
                                            )
            muchandler.assign_state(mucstate)
            return mucstate
        except RuntimeError, e:
            log.warning("Could not join room %s: %s" % (jid.as_string(), str(e)))
            return False

    def newRoomName(self, site):
        '''Return: new unpredictable and unique name for a MUC-room

           Argument:
           site - HelpIM Site object or string with the name of the site.
        '''
        if isinstance(site, str):
            sitename = site
        else:
            sitename = site.name
        basename = "%s_%s" % (sitename.strip(), newHash())
        if basename == self.__last_room_basename:
            self.__room_name_uniqifier += 1
        else:
            self.__room_name_uniqifier = 0
        self.__last_room_basename = basename
        newname = "%s.%d" % (basename, self.__room_name_uniqifier)
        return newname

    def kick(self, roomjid, nick):
        if isinstance(roomjid, str) or isinstance(roomjid, unicode):
            roomjid = str2roomjid(roomjid)
        log.info("Kicking user with nick '%s'." % nick)
        kickIq = MucIq(to_jid=roomjid, stanza_type="set")
        kickIq.make_kick_request(nick, reason=None)
        self.stream.send(kickIq)

    def makeModerator(self, roomjid, nick):
        if isinstance(roomjid, str) or isinstance(roomjid, unicode):
            roomjid = str2roomjid(roomjid)
        log.info("Making user with nick '%s' moderator." % nick)

        xml = "<iq to='%s' type='set' id='mod'><query xmlns='http://jabber.org/protocol/muc#admin'><item role='moderator' nick='%s'/></query></iq>" % (roomjid, nick)
        log.debug(xml)
        self.stream.write_raw(xml)
        
    def closeRooms(self, roomstatus=None, site=None):
        if site is None:
            # Resursively do all sites
            for name in self.sites.iterkeys():
                self.closeRooms(roomstatus, name)
            return
        if isinstance(site, str):
            sitename = site
        else:
            sitename = site.name
        site = self.sites[sitename]

        if roomstatus is None:
            rooms = site.rooms.getNotDestroyed() + site.groupRooms.getNotDestroyed()
        else:
            rooms = site.rooms.getByStatus(roomstatus) + site.groupRooms.getByStatus(roomstatus)
        for room in rooms:
            self.closeRoom(room)

    def closeRoom(self, room):
        roomjid = str2roomjid(room.jid)
        log.info("Closing down MUC-room '%s'." % room.jid)
        roomstate = self.mucmanager.rooms[unicode(roomjid)]
        roomstate.handler.closingDown = True
        mynick = roomstate.get_nick()
        for nick in roomstate.users.iterkeys():
            if nick != mynick:
                self.kick(roomjid, nick)
        log.info("Leaving MUC-room '%s'." % room.jid)
        room.destroyed()
        roomstate.leave()

    # Configuration access methods
    #

    # set_... methods: Methods to change settings that can be changed at runtime.
    #
    # Note: The set_... methods below return empty string on success, and error-string on failure.
    #       So using the returned value in conditional expressions may opposite of what you might expect.
    #
    def set_mucRoomPoolSize(self, newSize, site=None):
        '''Sets number of available rooms --> empty string on success. error-string on failure.

        If lowering number of rooms at runtime, the extra rooms in the pool will
        not be not be lowered immediately. The number of available rooms will decrease
        to the new pool size as rooms are taken into use.

        Arguments:
        newSize - string or int representing number of rooms to keep available for use. if newSize
                  is a string, it will be converted to an integer. 

        '''
        try:
            poolsize = int(self.conf.muc.poolsize)
        except ValueError:
            return "MUC-room pool size invalid"
        self.conf.muc['poolsize'] = newSize
        log.info("MUC-room pool size set to %s" % newSize)
        self.todo.append((self.fillMucRoomPool,))
        return str()

    # XMPP handler methods
    #
    def handle_message(self, s):
        if s.get_type() == "headline":
            return True
        log.stanza(s)
        message = u"Don't call us. We call you.."
        msg = Message(None, s.get_to(), s.get_from(), s.get_type(), None, None, message)
        self.stream.send(msg)
        self.printrooms()
        # for k,v in self.sites.iteritems():
        #     print 'Available for:', k
        #     for r in v.rooms.getAvailable():
        #         print r.jid

        #self.todo.append((self.closeRooms, None, 'Sensoor'))
        return True

    def printrooms(self):    #DBG:
        print "Rooms:"
        for r,v in self.mucmanager.rooms.iteritems():
            print r, "joined:", v.joined, "configured:", v.configured
            for u in v.users:
                print "users:", u

    def handle_presence_control(self, s):
        print "Incoming presence control request:", s.get_type()
        if s.get_type() == 'subscribe':
            self.stream.send(s.make_accept_response())
            return True
        # Ignore other requests
        return True


