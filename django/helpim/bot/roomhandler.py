from pyxmpp.jabber.muc import MucRoomManager, MucRoomHandler, MucRoomUser
from pyxmpp.jabber.muccore import MucPresence, MucIq, MucAdminQuery, MucItem

class RoomHandlerBase(MucRoomHandler):
    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        MucRoomHandler.__init__(self)
        self.mucmanager = bot.mucmanager
        self.kick = bot.kick
        self.makeModerator = bot.makeModerator
        self.todo = bot.todo
        self.closeRooms = bot.closeRooms
        self.fillMucRoomPool = bot.fillMucRoomPool
        self.site = site
        self.mucconf = mucconf
        self.password = password
        self.nick = nick
        self.userkicked = ''
        self.closingDown = False
        self.maxUsers = 10
        self.type = "Base"
        if rejoining:
            self.rejoinCount = 0
        else:
            self.rejoinCount = None

    def affiliation_changed(self, user, old_aff, new_aff, stanza):
        log.debug("Callback: affiliation_changed(%s, %s, %s, %s)" % (user, old_aff, new_aff, stanza))
        return True

    def configuration_form_received(self, form):
        log.debug("MUC-Room callback: configuration_form_received(%s)" % (form))
        log.debug("Configuring MUC-room '%s'" % self.room_state.room_jid.as_unicode())
        
        for field in form:
            if  field.name == u'allow_query_users':
                field.value = False
            elif field.name == u'muc#roomconfig_allowinvites':
                field.value = False
            elif field.name == u'muc#roomconfig_passwordprotectedroom':
                field.value = True
            elif field.name == u'muc#roomconfig_roomsecret':
                field.value = self.password
                log.debug("Setting MUC-room password to: '%s'" % self.password)
            elif field.name == u'muc#roomconfig_roomname':
                field.value = u'HelpIM'  # FIXME: Make this the name of the site the room belongs to?
            elif field.name == u'muc#roomconfig_persistentroom':
                field.value = False
            elif field.name == u'muc#roomconfig_publicroom':
                field.value = False
            elif field.name == u'public_list':
                field.value = False
            elif field.name == u'muc#roomconfig_maxusers':
                # Find lowest available option, but at least 3.
                maxusers = 9999999
                for option in field.options:
                    try:
                        value = int(option.values[0])
                    except ValueError:
                        log.warning("Form option for 'muc#roomconfig_maxusers' does not convert to int?")
                        log.warning("Option values received from server were: %s" % option.values)
                    if value >= self.maxusers and value < maxusers:
                        maxusers = value
                if maxusers == 0:
                    log.warning("Could not configure 'muc#roomconfig_maxusers'. No usable option found in form")
                    log.warning("Continuing with this option at default value, which is: %s" % field.value)
                else:
                    log.debug("Setting maxuser to %d." % maxusers)
                    field.value = unicode(maxusers)
            elif field.name == u'muc#roomconfig_whois':
                for option in field.options:
                    if option.values[0] == self.mucconf["whoisaccess"]:
                        field.value = unicode(self.mucconf["whoisaccess"])
                        break
                else:
                    log.warning("Configuration setting 'whoisaccess=\"%s\"' not valid according to form received from server" % self.mucconf["whoisaccess"])
                    log.warning("Continuing with this option at default value, which is: %s" % field.value)
            elif field.name == u'muc#roomconfig_membersonly':
                field.value = False
            elif field.name == u'muc#roomconfig_moderatedroom':
                field.value = False
            elif field.name == u'members_by_default':
                field.value = True
            elif field.name == u'muc#roomconfig_changesubject':
                allowchangesubject = str(self.mucconf["allowchangesubject"]).lower()
                field.value = (allowchangesubject=="yes" or allowchangesubject=="1" or allowchangesubject=="true")
            elif field.name == u'allow_private_messages':
                field.value = False
            elif field.name == u'allow_query_users':
                field.value = False
            elif field.name == u'muc#roomconfig_allowinvites':
                field.value = False
        log.form(form)
        form = form.make_submit(True)
        self.room_state.configure_room(form)
        return True

    def error(self, stanza):
        # Try to log messages that make sense from this information
        #
        errnode = stanza.get_error()
        stanzaclass = stanza.__class__.__name__
        errortype = str(errnode.get_type().lower())
        errormsg = errnode.get_message()

        # If our limit of presences in MUC-rooms is exceeded
        #
        if errortype == "cancel" and stanzaclass == "Presence":
            log.error("Could not create room '%s...'. Probably server limited number of presences in MUC-rooms."
                      % self.room_state.room_jid.as_unicode().split('@')[0][:30]
                      )
            log.error("XMPP error message was: '%s: %s'." % (errortype, errormsg))
        # FIXME:
        # elif <other known combination that may occur> :
        #    log.error(<message that makes sense>)
        
        log.debug("XMPP error type: '%s'.  PyXMPP error class: '%s'.  Message: '%s'." % (errortype, stanzaclass, errormsg))
        self.room_state.leave()
        self.mucmanager.forget(self.room_state)
        return True

    def nick_change(self, user, new_nick, stanza):
        #DBG log.debug("MUC-Room callback: nick_change(%s, %s, %s)" % (user, new_nick, stanza))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        log.debug("New nick = %s" % new_nick)
        return True

    def nick_changed(self, user, old_nick, stanza):
        #DBG log.debug("MUC-Room callback: nick_changed(%s, %s, %s)" % (user, old_nick, stanza))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        log.debug("New nick = %s" % old_nick)
        return True

    def presence_changed(self, user, stanza):
        #DBG log.debug("MUC-Room callback: presence_changed(%s, %s)" % (user, stanza))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        return False

    def role_changed(self, user, old_role, new_role, stanza):
        #DBG log.debug("Role changed: Old role = %s.  New role = %s" % (old_role, new_role))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        return True

    def room_configuration_error(self, stanza):
        log.error("MUC-Room callback: room_configuration_error(%s)" % (stanza))
        return True

    def room_created(self, stanza):
        log.debug("MUC-Room '%s' created" % self.room_state.room_jid.as_unicode())
        return True

    def subject_changed(self, user, stanza):
        log.debug("MUC-Room callback: subject_changed(%s, %s)" % (user, stanza))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        return True


class One2OneRoomHandler(RoomHandlerBase):

    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.maxUsers = 3
        self.type = "One2OneRoom"

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.rooms.newRoom(jidstr, self.password)
        log.debug("MUC-Room '%s' created and configured successfully" % jidstr)
        return True

    def message_received(self, user, stanza):
        room = self.get_helpim_room()
        if room is None or user is None or stanza.get_body() is None or stanza.get_body()[0:16] == "[#startuplines#]":
            return True
        if room.getStatus() == 'chatting':
            if user.nick == room.client_nick:
                try:
                    services.logCareSeekerChatMessage(conv_id=room.chat_id,
                                             messageText=stanza.get_body(),
                                             nickName=user.nick,
                                             databaseSession=self.site.session)
                except AttributeError:
                    log.error("Could not store message in database, chat id: %s, from: %s" % (str(room.chat_id), user.nick))
                else:
                    self.site.session.flush()
                    
            elif user.nick == room.staff_nick:
                try:
                    services.logCareWorkerChatMessage(conv_id=room.chat_id,
                                             messageText=stanza.get_body(),
                                             user_id=room.staff_id,
                                             nickName=room.staff_nick,
                                             databaseSession=self.site.session)
                except AttributeError:
                    log.error("Could not store message in database, chat id: %s, from: %s" % (str(room.chat_id), user.nick))
                else:
                    self.site.session.flush()
        #DBG log.debug("MUC-Room callback: message_received(). User = '%s'" % (user))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        return True

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            return True
        room = self.get_helpim_room()
        if room is None:
            return
        status = room.getStatus()
        log.debug("user with nick " + user.nick + " joined room " + room.jid + " with status: " + room.getStatus())
        if status == 'available':
            room.staffJoined()
            room.setStaffNick(user.nick)
            self.todo.append((self.fillMucRoomPool, self.site))
            log.info("Staff member entered room '%s'." % self.room_state.room_jid.as_unicode())
            self.rejoinCount = None
        elif status == 'availableForInvitation':
            room.staffJoined()
            room.setStaffNick(user.nick)
            self.todo.append((self.fillMucRoomPool, self.site))
            log.info("Staff member entered room for invitation '%s'." % self.room_state.room_jid.as_unicode())
            self.rejoinCount = None
        elif status == 'staffWaiting':
            if self.rejoinCount is None:
                room.clientJoined()
                room.setClientNick(user.nick)
                log.info("Client entered room '%s'." % self.room_state.room_jid.as_unicode())
            else:
                self.rejoinCount = None
                log.info("A user rejoined room '%s'." % self.room_state.room_jid.as_unicode())
        elif status == 'staffWaitingForInvitee':
            if self.rejoinCount is None:
                room.clientJoined()
                room.setClientNick(user.nick)
                log.info("Client entered room for invitation '%s'." % self.room_state.room_jid.as_unicode())
            else:
                # hmmm... this should happen, doesn't it?
                self.rejoinCount = None
                log.info("A user rejoined room for invitation '%s'." % self.room_state.room_jid.as_unicode())
        elif status == 'chatting':
            services.logChatEvent(conv_id=room.chat_id,
                         eventName="rejoin",
                         eventData="%s rejoind the chat" % user.nick,
                         databaseSession=self.site.session)
            self.site.session.flush()
            if self.rejoinCount is not None:
                self.rejoinCount += 1
                if self.rejoinCount == 2:
                    self.rejoinCount = None
                    log.info("The second user rejoined room '%s'." % self.room_state.room_jid.as_unicode())
        else:
            if self.rejoinCount is not None:
                log.error("User entered room '%s' while already in 'chatting' status!" % self.room_state.room_jid.as_unicode())
                log.error("Kicking user: Nick = '%s'" % user.nick)
                self.kick(self.room_state.room_jid.bare(), user.nick)
                self.userkicked = user.nick
        return False

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return False
        roomname = self.room_state.room_jid.as_unicode()
        if self.userkicked == user.nick or self.closingDown:
            self.userkicked = ''
            log.notice("Kicked user '%s' has left room '%s'." % (user.nick, roomname))
            return False
        room = self.get_helpim_room()
        roomstatus = room.getStatus()

        cleanexit = stanza.get_status()
        if cleanexit is not None and cleanexit.strip() == u"Clean Exit":
            cleanexit = True
        else:
            cleanexit = False

        if room is None:
            return False
        if roomstatus == 'staffWaiting':
            if cleanexit:
                log.notice("Staffmember waiting for chat has left room '%s' (clean exit)." % roomname)
                room.userLeftClean()
            else:
                log.notice("Staffmember waiting for chat has disappeared from room '%s' (un-clean exit)." % roomname)
                room.userLeftDirty()
        if roomstatus == 'staffWaitingForInvitee':
            if cleanexit:
                log.notice("Staffmember waiting for invitation chat has left room '%s' (clean exit)." % roomname)
                room.userLeftClean()
            else:
                log.notice("Staffmember waiting for invitation chat has disappeared from room '%s' (un-clean exit)." % roomname)
                room.userLeftDirty()

        elif roomstatus == 'chatting':
            if cleanexit:
                room.userLeftClean()
                log.info("A user left room '%s' (clean exit)." % self.room_state.room_jid.as_unicode())
                services.logChatEvent(conv_id=room.chat_id,
                             eventName="ended",
                             eventData="%s ended the chat" % user.nick,
                             databaseSession=self.site.session)
                self.site.session.flush()
            else:
                room.userLeftDirty()
                log.info("A user left room '%s' (un-clean exit)." % self.room_state.room_jid.as_unicode())
                services.logChatEvent(conv_id=room.chat_id,
                             eventName="left",
                             eventData="%s left the chat" % user.nick,
                             databaseSession=self.site.session)
                self.site.session.flush()
            log.info("User was: Nick = '%s'." % user.nick)
        elif roomstatus == 'closingChat':
            if cleanexit:
                room.userLeftClean()
                log.info("A user left room '%s' while the other user already left clean before (clean exit)." % self.room_state.room_jid.as_unicode())
            else:
                room.userLeftDirty()
                log.info("A user left room '%s' while the other user already left clean before (un-clean exit)." % self.room_state.room_jid.as_unicode())
            log.info("User was: Nick = '%s'." % user.nick)
        elif roomstatus == 'lost':
            if cleanexit:
                room.userLeftClean()
                log.info("A user left room '%s' while the other user already left unclean before (clean exit)." % self.room_state.room_jid.as_unicode())
            else:
                room.userLeftDirty()
                log.info("A user left room '%s' while the other user already left unclean before (un-clean exit)." % self.room_state.room_jid.as_unicode())
            log.info("User was: Nick = '%s'." % user.nick)
        else:
            log.warning("User left room '%s' while room was expected to be empty (roomstatus == %s)." % (roomname, roomstatus))
            log.info("User was: Nick = '%s'." % user.nick)
        return False

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.rooms.getByJid(jidstr)
        except KeyError:
            log.error("Could not find room '%s' in database." % jidstr)
            return None


class GroupRoomHandler(RoomHandlerBase):

    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.maxUsers = 30
        self.type = "GroupRoom"

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.groupRooms.newRoom(jidstr, self.password)
        log.debug("MUC-Room for groupchat '%s' created and configured successfully" % jidstr)
        return True

    def message_received(self, user, stanza):
        #try:
        if True:
            room = self.get_helpim_room()
            if room is None or user is None or stanza.get_body() is None:
                return True
            if room.getStatus() == 'chatting':
                groupServices.logChatgroupMessage(self.site, room.chat_id, user.nick, stanza.get_body())
        #except:
        #   log.error("Could not store groupchat message in database, chat id: %s, from: %s" % (str(room.chat_id), user.nick))
        log.debug("MUC-Room for groupchat callback: message_received(). User = '%s'" % (user))
        # DBG log.debug(stanza.serialize())
        # DBG log.stanza(stanza)
        # DBG log.user(user)
        return True

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.groupRooms.getByJid(jidstr)
        except KeyError:
            log.error("Could not find room '%s' in database." % jidstr)
            return None

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            return True
        room = self.get_helpim_room()
        if room is None:
            return
        status = room.getStatus()
        log.debug("user with nick " + user.nick + " joined group room " + room.jid + " with status: " + status)
        if status == "available":
            room.setStatus("chatting")
            log.info("User '%s' joined as first user group room '%s' for chat_id '%s'." % (user.nick, room.jid, room.chat_id))
        elif status == "abandoned":
            room.setStatus("chatting")
            log.info("User '%s' joined abandoned group room '%s' for chat_id '%s'." % (user.nick, room.jid, room.chat_id))
        elif status == "chatting":
            log.info("User '%s' joined room '%s' for chat_id '%s'." % (user.nick, room.jid, room.chat_id))
        else:
            log.warning("User '%s' joined room '%s' while not expected (roomstatus == %s)." % (user.nick, room.jid, status))
            return False

        groupMember = groupServices.getChatgroupMemberByMeetingIdAndNickname(self.site, room.chat_id, user.nick)
        if groupMember.is_admin:
            if not self.room_state.configured:
                log.warning("Should make participant moderator, but room is not configured. (Room: '%s')" % room.jid)
            if not self.room_state.me.affiliation=="admin" and not  self.room_state.me.affiliation=="owner":
                log.warning("Should make participant moderator, but bot is not admin. (Bot affiliation: '%s', Room: '%s')" % (self.room_state.me.affiliation, room.jid))
            log.info("Making user moderator: Nick = '%s'" % user.nick)
            self.makeModerator(self.room_state.room_jid.bare(), user.nick)

        #DBG log.debug("MUC-Room callback: user_joined(). User = '%s'" % (user))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        return False

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return False
        roomname = self.room_state.room_jid.as_unicode()
        room = self.get_helpim_room()

        groupServices.setChatgroupMeetingParticipantLeft(
            self.site,
            room.chat_id,
            user.nick)

        if self.userkicked == user.nick or self.closingDown:
            self.userkicked = ''
            log.notice("Kicked user '%s' has left room '%s'." % (user.nick, roomname))
            return False

        status = room.getStatus()
        nUsers = len(self.room_state.users) -1 # -1 for not counting the bot itself
        
        mucStatus = stanza.xpath_eval('d:x/d:status',
                                      {'d': 'http://jabber.org/protocol/muc#user'})

        if len(mucStatus) > 0:
            curAttr = mucStatus[0].properties
            while curAttr:
                if curAttr.name == 'code' and curAttr.content == '307':
                    """ this user must have been kicked. now we must make sure
                    to delete his access token and change the password for
                    this room
                    """
                    log.debug("############")
                    groupServices.setChatgroupMemberTokenInvalid(
                        self.site,
                        room.chat_id,
                        user.nick)
                    """ disabled resetting password as this would need to be done on xmpp level too and that's just too much work for now """
                    # password = unicode(newHash())
                    # room.setPassword(password)
                    break
                curAttr = curAttr.next
        
        cleanexit = stanza.get_status()
        if cleanexit is not None and cleanexit.strip() == u"Clean Exit":
            cleanexit = True
        else:
            cleanexit = False

        log.debug("user with nick " + user.nick + " left group room " + room.jid + " with status: " + status)
        if status == "chatting":
            if nUsers == 1:
                if cleanexit:
                    log.info("Last user '%s' left group room '%s' (clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
                    room.lastUserLeftClean()
                else:
                    log.info("Last user '%s' left group room '%s' (un-clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
                    room.lastUserLeftDirty()
            else:
                if cleanexit:
                    log.info("User '%s' left group room '%s' (clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
                else:
                    log.info("User '%s' left group room '%s' (un-clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
        else:
            log.warning("User '%s' left  room '%s' while room was expected to be empty (roomstatus == %s)." % (user.nick, room.jid, status))
            log.info("User was: Nick = '%s'." % user.nick)
        #DBG log.debug("MUC-Room callback: user_joined(). User = '%s'" % (user))
        #DBG log.stanza(stanza)
        #DBG log.user(user)
        return False

