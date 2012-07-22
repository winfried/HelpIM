import sys
import logging
import socket

from time import sleep
from signal import signal, alarm, SIGALRM
from datetime import datetime

from pyxmpp.jabber.client import JabberClient
from pyxmpp.jid import JID
from pyxmpp.message import Message
from pyxmpp.presence import Presence
from pyxmpp.iq import Iq

from pyxmpp.jabber.muc import MucRoomManager, MucRoomHandler
from pyxmpp.jabber.muccore import MucPresence

from django.utils.translation import ugettext as _

from forms_builder.forms.models import FormEntry

from helpim.common.models import EventLog
from helpim.conversations.models import Participant, ChatMessage
from helpim.rooms.models import getSites, AccessToken, One2OneRoom, GroupRoom, LobbyRoom, WaitingRoom, LobbyRoomToken, One2OneRoomToken, WaitingRoomToken, SimpleRoomToken
from helpim.questionnaire.models import Questionnaire, ConversationFormEntry

NS_HELPIM_ROOMS = "http://helpim.org/protocol/rooms"

logger = logging.getLogger(__name__)
def log_form(form):
    logger.debug("MUC-room configuration form ==BEGIN==")
    for field in form:
        logger.debug("  Field '%s':" % field.name)
        logger.debug("    Label = %s" % field.label)
        logger.debug("    Description = %s" % field.desc)
        logger.debug("    Type = %s" % field.type)
        logger.debug("    Required = %s" % field.required)
        logger.debug("    Value = %s" % field.value)
        logger.debug("    Options:")
        for option in field.options:
            logger.debug("      Label = %s" % option.label)
            logger.debug("      Values = %s" % option.values)
        logger.debug("    Values = %s" % field.values)
    logger.debug("MUC-room confugration form ==END==")

def log_stanza(stanza):
    stanzaType = stanza.get_stanza_type()
    objectType = None
    if isinstance(stanza, MucPresence):
        objectType = "MucPresence"
    elif isinstance(stanza, Presence):
        objectType = "Presence"
    elif isinstance(stanza, Message):
        objectType = "Message"
    logger.debug("Stanza log ==BEGIN==")
    logger.debug("  Stanza type = %s" % stanzaType)
    logger.debug("  XMPP object type = %s" % objectType)
    logger.debug("  From = %s" % stanza.get_from().as_unicode())
    logger.debug("  To   = %s" % stanza.get_from().as_unicode())
    if objectType == "Message":
        logger.debug("  Subject = %s" % stanza.get_subject())
        logger.debug("  Body = %s" % stanza.get_body())
    elif objectType == "Presence" or objectType == "MucPresence":
        logger.debug("  Priority = %s" % stanza.get_priority())
        logger.debug("  Status = %s" % stanza.get_status())
        logger.debug("  Show = %s" % stanza.get_show())
    elif objectType == "MucPresence":
        joininfo = stanza.get_join_info()
        logger.debug("  Password = %s" % joininfo.get_password())
        logger.debug("  History = %s" % joininfo.get_history())
        mucchild = stanza.get_muc_child()
        logger.debug("MUC child = %s" % mucchild)
    logger.debug("Stanza log ==END==")

def str2roomjid(jidstr):
    tmp = jidstr.split('@')
    node = tmp[0]
    domain = tmp[1].split('/')[0]
    roomjid = JID(node, domain)
    return roomjid

"""Utility function for using cryptografic Hashes in HelpIM"""
hash_initdone = False
def newHash():
    """Creates an unpredictable hash.
       Returns an 64 character long string, containing an
       hexadecimal encoded hash.
       Usage: hash = newHash()
    """
    import random
    from hashlib import sha256
    global hash_initdone
    if not hash_initdone:
        random.seed()
        hash_initdone = True
    string = str(datetime.now()) + str(random.random())
    hash = sha256(string).hexdigest()
    return hash

def get_questionnaire_entry_id(stanza):
    try:
        entry_id = stanza.xpath_eval('d:query/d:questionnaire',
                                     {'d': NS_HELPIM_ROOMS})[0]
        entry_id = entry_id.getContent()
        logger.debug("got entry id: %s" % entry_id)
        return entry_id
    except IndexError:
        logger.error("failed to parse questionnaires result paket from client with jid %s" % stanza.get_from())

class RoomHandlerBase(MucRoomHandler):
    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        MucRoomHandler.__init__(self)
        self.client = bot
        self.mucmanager = bot.mucmanager
        self.kick = bot.kick
        self.makeModerator = bot.makeModerator
        self.todo = bot.todo
        self.closeRooms = bot.closeRooms
        self.fillMucRoomPool = bot.fillMucRoomPool
        self.inviteClients = bot.inviteClients
        self.stream = bot.stream
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
        logger.debug("Callback: affiliation_changed(%s, %s, %s, %s)" % (user, old_aff, new_aff, stanza))
        return True

    def configuration_form_received(self, form):
        logger.debug("MUC-Room callback: configuration_form_received(%s)" % (form))
        logger.debug("Configuring MUC-room '%s'" % self.room_state.room_jid.as_unicode())

        # prosody as of 0.8.2 misses a field in its configuration - we
        # check for it manually to fix this client side
        field_passwordprotectedroom_beenthere_donethat = False

        for field in form:
            if  field.name == u'allow_query_users':
                field.value = False
            elif field.name == u'muc#roomconfig_allowinvites':
                field.value = False
            elif field.name == u'muc#roomconfig_passwordprotectedroom':
                field_passwordprotectedroom_beenthere_donethat = True
                field.value = 1
            elif field.name == u'muc#roomconfig_roomsecret':
                field.value = self.password
                logger.debug("Setting MUC-room password to: '%s'" % self.password)
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
                        logger.warning("Form option for 'muc#roomconfig_maxusers' does not convert to int?")
                        logger.warning("Option values received from server were: %s" % option.values)
                    if value >= self.maxusers and value < maxusers:
                        maxusers = value
                if maxusers == 0:
                    logger.warning("Could not configure 'muc#roomconfig_maxusers'. No usable option found in form")
                    logger.warning("Continuing with this option at default value, which is: %s" % field.value)
                else:
                    logger.debug("Setting maxuser to %d." % maxusers)
                    field.value = unicode(maxusers)
            elif field.name == u'muc#roomconfig_whois':
                for option in field.options:
                    if option.values[0] == self.mucconf["whoisaccess"]:
                        field.value = unicode(self.mucconf["whoisaccess"])
                        break
                else:
                    logger.warning("Configuration setting 'whoisaccess=\"%s\"' not valid according to form received from server" % self.mucconf["whoisaccess"])
                    logger.warning("Continuing with this option at default value, which is: %s" % field.value)
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

        # prosody misses this one from its configuration form
        if not field_passwordprotectedroom_beenthere_donethat:
            form.add_field(name=u'muc#roomconfig_passwordprotectedroom',
                           value=True)

        log_form(form)
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
        logger.debug("XMPP error type: '%s'.  PyXMPP error class: '%s'.  Message: '%s'." % (errortype, stanzaclass, errormsg))
        return True

    def nick_change(self, user, new_nick, stanza):
        logger.debug("New nick = %s" % new_nick)
        return True

    def nick_changed(self, user, old_nick, stanza):
        logger.debug("New nick = %s" % old_nick)
        return True

    def presence_changed(self, user, stanza):
        return False

    def role_changed(self, user, old_role, new_role, stanza):
        return True

    def room_configuration_error(self, stanza):
        logger.error("MUC-Room callback: room_configuration_error(%s)" % (stanza))
        return True

    def room_created(self, stanza):
        logger.debug("MUC-Room '%s' created" % self.room_state.room_jid.as_unicode())
        return True

    def subject_changed(self, user, stanza):
        logger.debug("MUC-Room callback: subject_changed(%s, %s)" % (user, stanza))
        room = self.get_helpim_room()
        if not room is None and not room.chat is None:
            chat = room.chat
            chat.subject = stanza.get_subject()
            chat.save()
        return True

    # TODO that should rather go to our own subclassed MucRoomState
    def send_private_message(self, nick, body):
        to_jid = self.room_state.get_room_jid(nick)
        m = Message(to_jid=to_jid, stanza_type='chat', body=body)
        self.client.stream.send(m)

    def send_queue_update(self, nick, pos):
        self.send_private_message(nick, _("You're at position %(pos)d of the waiting queue.") % {'pos': pos})

    def send_questionnaire(self, user_jid, questionnaire_url,
                           result_handler=None, error_handler=None):
        iq = Iq(stanza_type='set')
        iq.set_to(user_jid)
        query = iq.new_query(NS_HELPIM_ROOMS)
        n = query.newChild(None, 'questionnaire', None)
        n.setProp('url', questionnaire_url)
        query.addChild(n)

        if result_handler is None:
            result_handler = self.__questionnaire_result
        if error_handler is None:
            error_handler = self.__questionnaire_error

        # setup result handler
        self.client.stream.set_response_handlers(
            iq,
            result_handler,
            error_handler,
            )

        self.client.stream.send(iq)

    def __questionnaire_result(self, stanza):
        log_stanza(stanza)

    def __questionnaire_error(self, stanza):
        log_stanza(stanza)

class One2OneRoomHandler(RoomHandlerBase):

    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.maxUsers = 3
        self.type = "One2OneRoom"

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.rooms.newRoom(jidstr, self.password)
        logger.debug("MUC-Room '%s' created and configured successfully" % jidstr)
        return True

    def message_received(self, user, stanza):
        room = self.get_helpim_room()

        if room is None or user is None or stanza.get_body() is None or stanza.get_body()[0:16] == "[#startuplines#]":
            return True

        if room.getStatus() != 'chatting':
            return True

        chatmessage = ChatMessage(event='message', conversation=room.chat, body=stanza.get_body(), sender_name=user.nick)

        if user.nick == room.client_nick:
            chatmessage.sender = room.client
        elif user.nick == room.staff_nick:
            chatmessage.sender = room.staff

        chatmessage.save()

        # if careseeker and careworker are present (status chatting) and this was the first message,
        # then this first message marks the start of the conversation
        if room.getStatus() == 'chatting' and room.chat.messages.filter(chatmessage__event='message').count() == 1:
            room.chat.started_at = chatmessage.created_at
            room.chat.save()

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            logger.info("user joined with self nick '%s'" % user.nick)
            return True

        room = self.get_helpim_room()

        if room is None:
            logger.info("get_helpim_room returned None")
            return

        # log event when careseeker has joined
        accessToken = AccessToken.objects.get(jid=user.real_jid)
        if accessToken.role == Participant.ROLE_CLIENT:
            EventLog(type='helpim.rooms.one2one.client_joined', session=accessToken.token, payload=room.chat.pk).save()

        status = room.getStatus()
        logger.info("user with nick " + user.nick + " joined room " + room.jid + " with status: " + room.getStatus())

        if status == 'available':
            room.staffJoined(user)
            chatmessage = ChatMessage(event='join', conversation=room.chat, sender=room.staff, sender_name=user.nick)
            self.todo.append((self.fillMucRoomPool, self.site))
            logger.info("Staff member entered room '%s'." % self.room_state.room_jid.as_unicode())
            self.rejoinCount = None

            """ send invite to a client """
            try:
                # probably this could be done in one step
                token = LobbyRoomToken.objects.get(token__jid=user.real_jid)
                waitingRoom = WaitingRoom.objects.filter(status='chatting').filter(lobbyroom=token.room)[0]
                self.todo.append((self.inviteClients, waitingRoom))
            except IndexError:
                logger.warning("no waiting room found for lobby with jid %s" % token.room.jid)
                # wheee
                pass

        elif status == 'availableForInvitation':
            room.staffJoined(user)
            chatmessage = ChatMessage(event='join', conversation=room.chat, sender_name=user.nick, sender=room.staff)
            self.todo.append((self.fillMucRoomPool, self.site))
            logger.info("Staff member entered room for invitation '%s'." % self.room_state.room_jid.as_unicode())
            self.rejoinCount = None
        elif status == 'staffWaiting':
            if self.rejoinCount is None:
                formEntry = room.clientJoined(user)
                chatmessage = ChatMessage(event='join', conversation=room.chat, sender_name=user.nick, sender=room.client)
                if not formEntry is None:
                    # tell staff about
                    self.send_private_message(room.staff_nick, _("%(nick)s filled in a questionnaire: %(domain)s/forms/entry/%(id)d/") % {'nick':user.nick, 'domain':self.mucconf.http_domain, 'id':formEntry.pk})
                logger.info("Client entered room '%s'." % self.room_state.room_jid.as_unicode())
            else:
                self.rejoinCount = None
                chatmessage = ChatMessage(event='rejoin', conversation=room.chat, sender_name=user.nick, sender=room.client)
                logger.info("A user rejoined room '%s'." % self.room_state.room_jid.as_unicode())
        elif status == 'staffWaitingForInvitee':
            if self.rejoinCount is None:
                room.clientJoined(user)
                chatmessage = ChatMessage(event='join', conversation=room.chat, sender_name=user.nick, sender=room.client)
                logger.info("Client entered room for invitation '%s'." % self.room_state.room_jid.as_unicode())
            else:
                # hmmm... this should happen, doesn't it?
                self.rejoinCount = None
                chatmessage = ChatMessage(event='rejoin', conversation=room.chat, sender_name=user.nick, sender=room.client)
                logger.info("A user rejoined room for invitation '%s'." % self.room_state.room_jid.as_unicode())
        elif status == 'chatting':

            chatmessage = ChatMessage(event='rejoin', conversation=room.chat, sender_name=user.nick)
            if user.nick == room.client_nick:
                chatmessage.sender = room.staff
            elif user.nick == room.staff_nick:
                chatmessage.sender = room.client

            if self.rejoinCount is not None:
                self.rejoinCount += 1
                if self.rejoinCount == 2:
                    self.rejoinCount = None
                    logger.info("The second user rejoined room '%s'." % self.room_state.room_jid.as_unicode())
        else:
            if self.rejoinCount is not None:
                logger.error("User entered room '%s' while already after 'chatting' status!" % self.room_state.room_jid.as_unicode())
                logger.error("Kicking user: Nick = '%s'" % user.nick)
                self.kick(self.room_state.room_jid.bare(), user.nick)
                self.userkicked = user.nick
            return False

        chatmessage.save()

        return False

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return False
        roomname = self.room_state.room_jid.as_unicode()
        if self.userkicked == user.nick or self.closingDown:
            self.userkicked = ''
            logger.warning("Kicked user '%s' has left room '%s'." % (user.nick, roomname))
            return False
        room = self.get_helpim_room()
        roomstatus = room.getStatus()

        cleanexit = stanza.get_status()
        if cleanexit is not None and cleanexit.strip() == u"Clean Exit":
            cleanexit = True
        else:
            cleanexit = False

        # TODO somehow unify setting sender and dealing with exceptions
        # if is_staff:
        #     sender = room.staff
        # else:
        #     sender = room.client

        if room is None:
            return False
        if roomstatus == 'staffWaiting':
            if cleanexit:
                logger.warning("Staffmember waiting for chat has left room '%s' (clean exit)." % roomname)
                room.userLeftClean()
            else:
                logger.warning("Staffmember waiting for chat has disappeared from room '%s' (un-clean exit)." % roomname)
                room.userLeftDirty()
        elif roomstatus == 'staffWaitingForInvitee':
            if cleanexit:
                logger.warning("Staffmember waiting for invitation chat has left room '%s' (clean exit)." % roomname)
                room.userLeftClean()
            else:
                logger.warning("Staffmember waiting for invitation chat has disappeared from room '%s' (un-clean exit)." % roomname)
                room.userLeftDirty()

        elif roomstatus == 'chatting':
            if cleanexit:
                room.userLeftClean()
                logger.info("A user left room '%s' (clean exit)." % self.room_state.room_jid.as_unicode())
                chatmessage = ChatMessage(event='ended', conversation=room.chat, sender_name=user.nick)
            else:
                room.userLeftDirty()
                chatmessage = ChatMessage(event='left', conversation=room.chat, sender_name=user.nick)
                logger.info("A user left room '%s' (un-clean exit)." % self.room_state.room_jid.as_unicode())

            if user.nick == room.client_nick:
                chatmessage.sender = room.staff
            elif user.nick == room.staff_nick:
                chatmessage.sender = room.client

            chatmessage.save()

            logger.info("User was: Nick = '%s'." % user.nick)
        elif roomstatus == 'closingChat':
            if cleanexit:
                room.userLeftClean()
                chatmessage = ChatMessage(event='ended', conversation=room.chat, sender_name=user.nick)
                logger.info("A user left room '%s' while the other user already left clean before (clean exit)." % self.room_state.room_jid.as_unicode())
            else:
                room.userLeftDirty()
                chatmessage = ChatMessage(event='left', conversation=room.chat, sender_name=user.nick)
                logger.info("A user left room '%s' while the other user already left clean before (un-clean exit)." % self.room_state.room_jid.as_unicode())

            if user.nick == room.client_nick:
                chatmessage.sender = room.staff
            elif user.nick == room.staff_nick:
                chatmessage.sender = room.client

            chatmessage.save()

            logger.info("User was: Nick = '%s'." % user.nick)
        elif roomstatus == 'lost':
            if cleanexit:
                room.userLeftClean()
                logger.info("A user left room '%s' while the other user already left unclean before (clean exit)." % self.room_state.room_jid.as_unicode())
            else:
                room.userLeftDirty()
                logger.info("A user left room '%s' while the other user already left unclean before (un-clean exit)." % self.room_state.room_jid.as_unicode())
            logger.info("User was: Nick = '%s'." % user.nick)
        else:
            logger.warning("User left room '%s' while room was expected to be empty (roomstatus == %s)." % (roomname, roomstatus))
            logger.info("User was: Nick = '%s'." % user.nick)

        # request questionnaire from participant

        # determine type of user
        is_staff = False
        if user.nick == room.staff_nick:
            is_staff = True

        # set position and callback for questionnaire results (formEntry)
        if is_staff:

            # first check if we had a client in the room otherwise we don't need to ask anything
            if room.client is None:
                return

            position = 'SA'
        else:
            position = 'CA'

        # check for questionnaire
        try:
            questionnaire = Questionnaire.objects.filter(position=position)[0]

            # send along
            self.send_questionnaire(user_jid=user.real_jid,
                                    questionnaire_url=questionnaire.get_absolute_url(),
                                    result_handler=lambda stanza: self.__create_conversation_form_entry(stanza, position))
        except IndexError:
            # no milk today
            pass
        return False

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.rooms.getByJid(jidstr)
        except One2OneRoom.DoesNotExist:
            logger.error("Could not find room '%s' in database." % jidstr)
            return None

    def __questionnaire_result_for_staff(self, stanza):
        self.__create_conversation_form_entry(stanza, 'SA')

    def __questionnaire_result_for_client(self, stanza):
        self.__create_conversation_form_entry(stanza, 'CA')

    def __create_conversation_form_entry(self, stanza, position):
        try:
            room = self.get_helpim_room()
            if room is None:
                logger.warning("get_helpim_room couldn't find a room")
                return
            # For now we assume that the questionnaire hasn't changed
            # in between sending and receiving it. The correct
            # solution would be to store the ConversationFormEntry
            # when sending the quesitonnaire and to only attach the
            # entry when receiving the result. This could be done by
            # storing the ConversationFormEntry with the user's token.x
            questionnaire = Questionnaire.objects.filter(position=position)[0]

            entry_id = get_questionnaire_entry_id(stanza)
            entry = FormEntry.objects.get(pk=entry_id)

            ConversationFormEntry.objects.create(
                questionnaire = questionnaire,
                entry = entry,
                conversation = room.chat,
                position = position)

        except FormEntry.DoesNotExist:
            logger.error("unable to find form entry from %s for id given %s" % (stanza.get_from(), entry_id))

class SimpleRoomHandler(RoomHandlerBase):
    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.type = "SimpleRoom"

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.simpleRooms.getByJid(jidstr)
        except One2OneRoom.DoesNotExist:
            logger.error("Could not find room '%s' in database." % jidstr)
            return None

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.simpleRooms.newRoom(jidstr, self.password)
        logger.debug("MUC-Room for simpleRoom '%s' created and configured successfully" % jidstr)
        return True

    def message_received(self, user, stanza):
        room = self.get_helpim_room()

        if room is None or user is None or stanza.get_body() is None or stanza.get_body()[0:16] == "[#startuplines#]":
            return True

        if room.getStatus() != 'chatting':
            return True

        chatmessage = ChatMessage(event='message', conversation=room.chat, body=stanza.get_body(), sender_name=user.nick)

        if user.nick == room.client_nick:
            chatmessage.sender = room.client
        elif user.nick == room.staff_nick:
            chatmessage.sender = room.staff

        chatmessage.save()

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            logger.info("user joined with self nick '%s'" % user.nick)
            return True

        room = self.get_helpim_room()

        if room is None:
            logger.info("get_helpim_room returned None")
            return

        status = room.getStatus()
        logger.info("user with nick " + user.nick + " joined room " + room.jid + " with status: " + status)
        if status == 'available':
            self.todo.append((self.fillMucRoomPool, self.site))

        room.userJoined(user)
        # must be done after call to userJoined as only after we can be sure there's a conversation
        if status in ('available', 'waiting'):
            ChatMessage.objects.create(event='join', conversation=room.chat, sender_name=user.nick, sender=room.getParticipantByNick(user.nick))
        else:
            ChatMessage.objects.create(event='rejoin', conversation=room.chat, sender_name=user.nick, sender=room.getParticipantByNick(user.nick))

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return False
        roomname = self.room_state.room_jid.as_unicode()
        if self.userkicked == user.nick or self.closingDown:
            self.userkicked = ''
            logger.warning("Kicked user '%s' has left room '%s'." % (user.nick, roomname))
            return False
        room = self.get_helpim_room()

        cleanexit = stanza.get_status()
        if cleanexit is not None and cleanexit.strip() == u"Clean Exit":
            ChatMessage.objects.create(event='ended', conversation=room.chat, sender_name=user.nick, sender=room.getParticipantByNick(user.nick))
            room.userLeftClean()
        else:
            ChatMessage.objects.create(event='left', conversation=room.chat, sender_name=user.nick, sender=room.getParticipantByNick(user.nick))
            room.userLeftDirty()

class GroupRoomHandler(RoomHandlerBase):

    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.maxUsers = 30
        self.type = "GroupRoom"

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.groupRooms.newRoom(jidstr, self.password)
        logger.debug("MUC-Room for groupchat '%s' created and configured successfully" % jidstr)
        return True

    def message_received(self, user, stanza):
        room = self.get_helpim_room()

        if room is None or user is None or stanza.get_body() is None:
            return True

        if room.getStatus() == 'chatting':
            chatmessage = ChatMessage(event='message', conversation=room.chat, body=stanza.get_body(), sender_name=user.nick)
            chatmessage.save()

        logger.debug("MUC-Room for groupchat callback: message_received(). User = '%s'" % (user))

        return True

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.groupRooms.getByJid(jidstr)
        except GroupRoom.DoesNotExist:
            logger.error("Could not find room '%s' in database." % jidstr)
            return None

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            return True
        room = self.get_helpim_room()
        if room is None:
            return
        status = room.getStatus()
        logger.debug("user with nick " + user.nick + " joined group room " + room.jid + " with status: " + status)
        if status == "available":
            room.setStatus("chatting")
            logger.info("User '%s' joined as first user group room '%s' for chat_id '%s'." % (user.nick, room.jid, room.chat_id))
        elif status == "abandoned":
            room.setStatus("chatting")
            logger.info("User '%s' joined abandoned group room '%s' for chat_id '%s'." % (user.nick, room.jid, room.chat_id))
        elif status == "chatting":
            logger.info("User '%s' joined room '%s' for chat_id '%s'." % (user.nick, room.jid, room.chat_id))
        else:
            logger.warning("User '%s' joined room '%s' while not expected (roomstatus == %s)." % (user.nick, room.jid, status))
            return False

        groupMember = Participant.objects.get(room=room, name=user.nick)

        if groupMember.role == Participant.ROLE_STAFF:
            if not self.room_state.configured:
                logger.warning("Should make participant moderator, but room is not configured. (Room: '%s')" % room.jid)
            if not self.room_state.me.affiliation=="admin" and not  self.room_state.me.affiliation=="owner":
                logger.warning("Should make participant moderator, but bot is not admin. (Bot affiliation: '%s', Room: '%s')" % (self.room_state.me.affiliation, room.jid))
            logger.info("Making user moderator: Nick = '%s'" % user.nick)
            self.makeModerator(self.room_state.room_jid.bare(), user.nick)

        return False

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return False

        roomname = self.room_state.room_jid.as_unicode()
        room = self.get_helpim_room()

        if self.userkicked == user.nick or self.closingDown:
            self.userkicked = ''
            logger.warning("Kicked user '%s' has left room '%s'." % (user.nick, roomname))
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
                    # FIXME implement
                    break
                curAttr = curAttr.next

        cleanexit = stanza.get_status()
        if cleanexit is not None and cleanexit.strip() == u"Clean Exit":
            cleanexit = True
        else:
            cleanexit = False

        logger.debug("user with nick " + user.nick + " left group room " + room.jid + " with status: " + status)
        if status == "chatting":
            if nUsers == 1:
                if cleanexit:
                    logger.info("Last user '%s' left group room '%s' (clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
                    room.lastUserLeftClean()
                else:
                    logger.info("Last user '%s' left group room '%s' (un-clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
                    room.lastUserLeftDirty()
            else:
                if cleanexit:
                    logger.info("User '%s' left group room '%s' (clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
                else:
                    logger.info("User '%s' left group room '%s' (un-clean exit, chat_id == '%s')." % (user.nick, room.jid, room.chat_id))
        else:
            logger.warning("User '%s' left  room '%s' while room was expected to be empty (roomstatus == %s)." % (user.nick, room.jid, status))
            logger.info("User was: Nick = '%s'." % user.nick)
        return False

class LobbyRoomHandler(RoomHandlerBase):
    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.type = "LobbyRoom"
        self.userCount = 0

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.lobbyRooms.newRoom(jidstr, self.password)
        logger.debug("MUC-Room for lobby '%s' created and configured successfully" % jidstr)
        return True

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.lobbyRooms.getByJid(jidstr)
        except LobbyRoom.DoesNotExist:
            logger.error("Could not find room '%s' in database." % jidstr)
            return None

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            return True
        if self.userCount == 0:
            """ first user has joined """
            room = self.get_helpim_room()
            if not room is None:
                room.setStatus('chatting')

                """ now get a waiting room to be associated with this lobby """
                waitingroom = WaitingRoom.objects.filter(status='available')[0]
                waitingroom.lobbyroom = room
                waitingroom.setStatus('abandoned')

        self.userCount += 1
        self.todo.append((self.fillMucRoomPool, self.site))

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return True
        self.userCount -= 1
        if self.userCount == 0:
            room = self.get_helpim_room()
            if room is None:
                return
            """ if associated waitingroom is empty too it's save to remove all """
            try:
                waitingroom = WaitingRoom.objects.filter(lobbyroom=room).filter(status='abandoned')[0]
                room.setStatus('toDestroy')
                waitingroom.setStatus('toDestroy')
            except IndexError:
                room.setStatus('abandoned')

class WaitingRoomHandler(RoomHandlerBase):
    def __init__(self, bot, site, mucconf, nick, password, rejoining=False):
        RoomHandlerBase.__init__(self, bot, site, mucconf, nick, password, rejoining)
        self.type = "WaitingRoom"
        self.userCount = 0

    def room_configured(self):
        jidstr = self.room_state.room_jid.bare().as_unicode()
        self.site.waitingRooms.newRoom(jidstr, self.password)
        logger.debug("MUC-Room for waiting room '%s' created and configured successfully" % jidstr)
        return True

    def get_helpim_room(self):
        '''Return the HelpIM-API room-object which this handler handles'''
        jidstr = self.room_state.room_jid.bare().as_unicode()
        try:
            return self.site.waitingRooms.getByJid(jidstr)
        except WaitingRoom.DoesNotExist:
            logger.error("Could not find room '%s' in database." % jidstr)
            return None

    def user_joined(self, user, stanza):
        if user.nick == self.nick:
            return True

        room = self.get_helpim_room()
        if room is None:
            return

        ready = True

        waitingRoomToken = WaitingRoomToken.objects.get(token__jid=user.real_jid)

        try:
            questionnaire = Questionnaire.objects.filter(position='CB')[0]

            # send iq set to client to inform about questionnaire. we
            # set him to not being ready first and to True once he's
            # finished with the questionnaire.

            waitingRoomToken.ready = False

            conversation_form_entry = ConversationFormEntry.objects.create(questionnaire=questionnaire, position='CB')
            waitingRoomToken.conversation_form_entry = conversation_form_entry
            waitingRoomToken.save()

            ready = False

            self.send_questionnaire(user_jid=user.real_jid,
                                    questionnaire_url=questionnaire.get_absolute_url(),
                                    result_handler=self.__questionnaire_result)

        except IndexError:
            # no questionnaire no fun!
            # waitingtime for careseeker starts now
            EventLog(type='helpim.rooms.waitingroom.joined', session=waitingRoomToken.token.token).save()

        room.addClient(user, ready)
        if ready:
            self.send_queue_update(user.nick, room.getWaitingPos(user))

        self.todo.append((self.inviteClients, room))
        if self.userCount == 0:
            room.setStatus('chatting')
        self.userCount += 1
        self.todo.append((self.fillMucRoomPool, self.site))

    def user_left(self, user, stanza):
        if user.nick == self.nick:
            return True

        logger.debug("user left waiting room: %s" % user.nick)

        try:
            accessToken = AccessToken.objects.get(jid=user.real_jid)
            EventLog(type='helpim.rooms.waitingroom.left', session=accessToken.token).save()
        except AccessToken.DoesNotExist:
            """ this shouldn't happen """
            logger.warning("got no access token for user with jid %s" % user.real_jid)

        self.userCount -= 1
        room = self.get_helpim_room()
        if room is None:
            return

        room.removeClient(user)

        for client in room.getWaitingClients():
            logger.debug("sending update to %s" % client.nick)
            self.send_queue_update(client.nick, room.getWaitingPos(client))

        if self.userCount > 0:
            return
        if not room.lobbyroom is None:
            if room.lobbyroom.getStatus() == 'abandoned':
                """ both rooms are abandoned """
                room.lobbyroom.setStatus('toDestroy')
                room.setStatus('toDestroy')
            elif room.lobbyroom.getStatus() == 'chatting':
                room.setStatus('abandoned')
            else:
                room.setStatus('toDestroy')
        else:
            room.setStatus('toDestroy')

    def __questionnaire_result(self, stanza):
        log_stanza(stanza)

        room = self.get_helpim_room()
        if room is None:
            return

        user = self.room_state.get_user(stanza.get_from())
        room.setClientReady(user, True)
        self.send_queue_update(user.nick, room.getWaitingPos(user))

        token = WaitingRoomToken.objects.get(token__jid=stanza.get_from())

        token.ready = True

        # waitingtime for careseeker starts now after he has submitted questionnaire
        EventLog(type='helpim.rooms.waitingroom.joined', session=token.token.token).save()

        # link questionnaire to token
        try:
            entry_id = get_questionnaire_entry_id(stanza)
            entry = FormEntry.objects.get(pk=entry_id)
            conversationFormEntry = token.conversation_form_entry
            conversationFormEntry.entry = entry
            conversationFormEntry.entry_at = datetime.now()
            conversationFormEntry.save()
        except FormEntry.DoesNotExist:
            logger.error("unable to find form entry from %s for id given %s" % (stanza.get_from(), entry_id))

        token.save()
        self.todo.append((self.inviteClients, room))

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
        self.sites = getSites()

        self.iqID = 0

    def getIqID(self):
        self.iqID += 1
        return self.iqID

    def roomCleanup(self):
        for name, site in self.sites.iteritems():
            # One2OneRooms
            for room in site.rooms.getToDestroy():
                logger.info("Closing room %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for status in 'lost', 'closingChat', 'abandoned':
                for room in site.rooms.getTimedOut(status, int(self.conf.mainloop.cleanup)):
                    logger.warning("Closing room %s which has timed out in '%s' status." % (room.jid, status))
                    self.closeRoom(room)
            for room in site.rooms.getHangingStaffStart(int(self.conf.mainloop.cleanup)):
                logger.warning("Closing room %s which is has timed out while waiting for staff to enter room" % (room.jid))
                self.closeRoom(room)
            site.rooms.deleteClosed()
            # GroupRooms
            for room in site.groupRooms.getToDestroy():
                logger.info("Closing groupRoom %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for room in site.groupRooms.getTimedOut('abandoned', int(self.conf.mainloop.cleanup)):
                logger.warning("Closing groupRoom %s which has timed out in '%s' status." % (room.jid, status))
                self.closeRoom(room)
            site.groupRooms.deleteClosed()
            # LobbyRooms
            for room in site.lobbyRooms.getToDestroy():
                logger.info("Closing lobbyRoom %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for room in site.lobbyRooms.getTimedOut('abandoned', int(self.conf.mainloop.cleanup)):
                logger.warning("Closing lobbyRoom %s which has timed out in '%s' status." % (room.jid, status))
                self.closeRoom(room)
            site.lobbyRooms.deleteClosed()
            # WaitingRooms
            for room in site.waitingRooms.getToDestroy():
                logger.info("Closing waitingRoom %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for room in site.waitingRooms.getTimedOut('abandoned', int(self.conf.mainloop.cleanup)):
                logger.warning("Closing waitingRoom %s which has timed out in '%s' status." % (room.jid, status))
                self.closeRoom(room)
            site.waitingRooms.deleteClosed()
            # SimpleRooms
            for room in site.simpleRooms.getToDestroy():
                logger.info("Closing simpleRoom %s which was not used anymore." % room.jid)
                self.closeRoom(room)
            for room in site.simpleRooms.getTimedOut('abandoned', int(self.conf.mainloop.cleanup)):
                logger.warning("Closing simpleRoom %s which has timed out in '%s' status." % (room.jid, status))
                self.closeRoom(room)
            site.simpleRooms.deleteClosed()
        #DBG: self.printrooms()

    def alarmHandler(self, signum, frame):
        # Assumes only to be called for alarm signal: Ignores arguments
        self.cleanup = True

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
                    self.__lost_connection = True
                    logger.critical("Lost connection. Trying to reconnect every %d seconds" % reconnectdelay)
                    reconnectcount = 1
                    self.stats.connectionLost += 1
                    while True:
                        try:
                            sleep(reconnectdelay)
                            self.connect()
                        except socket.error:
                            reconnectcount += 1
                            logger.warning("Tried to reconnect %d times. Trying again in %d seconds" % (reconnectcount, reconnectdelay))
                        else:
                            logger.warning("Reconnected  after %d attempts" % reconnectcount)
                            break
                self.stats.mainloopcount += 1
                if self.stats.mainloopcount >= sys.maxint:
                    self.stats.mainloopcount = 0
                    self.stats.busycount = 0

        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt. Exit...")
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
        self.stream.set_iq_get_handler("query", NS_HELPIM_ROOMS, self.handle_iq_get_room)
        self.stream.set_iq_get_handler("conversationId", NS_HELPIM_ROOMS, self.handle_iq_get_conversationId)
        self.stream.set_iq_set_handler("block", NS_HELPIM_ROOMS, self.handle_iq_set_block_participant)

    def getMucSettings(self, site):
        '''Return dict with global MUC-settings merged with site-specific MUC-settings'''
        return self.conf.muc

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
        logger.info("Refilling room pool for '%s'." % sitename)
        mucconf = self.getMucSettings(sitename)
        mucdomain = mucconf["domain"]
        poolsize = int(mucconf["poolsize"])

        # FIXME: only create rooms of the type(s) needed
        rooms = [{'nAvailable': len(site.rooms.getAvailable()),
                  'handler': One2OneRoomHandler},
                 {'nAvailable': len(site.groupRooms.getAvailable()),
                  'handler': GroupRoomHandler},
                 {'nAvailable': len(site.lobbyRooms.getAvailable()),
                  'handler': LobbyRoomHandler},
                 {'nAvailable': len(site.waitingRooms.getAvailable()),
                  'handler': WaitingRoomHandler},
                 {'nAvailable': len(site.simpleRooms.getAvailable()),
                  'handler': SimpleRoomHandler}]
        for room in rooms:
            self.__createRooms(site, mucdomain, poolsize, room['nAvailable'], room['handler'])

    def __createRooms(self, site, mucdomain, poolsize, nAvailable, handler):
        sitename = site.name
        nToCreate =  poolsize - nAvailable
        logger.info("Pool size for site '%s' = %d.  Currently available rooms = %d." % (sitename, poolsize, nAvailable))
        logger.info("Creating %d new rooms for site '%s'." % (nToCreate, sitename))
        for tmp in range(nToCreate):
            roomname = self.newRoomName(sitename)
            password = unicode(newHash())
            logger.info("Creating MUC-room '%s@%s'." % (roomname, mucdomain))
            mucstate = self.joinMucRoom(site, JID(roomname, mucdomain), password, handler)
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
                logger.warning("Re-joining room '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, One2OneRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixroomstatus(room, mucstate)
            for room in site.groupRooms.getNotDestroyed():
                logger.warning("Re-joining groupRoom '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, GroupRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixgrouproomstatus(room, mucstate)
            for room in site.lobbyRooms.getNotDestroyed():
                logger.warning("Re-joining lobbyRoom '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, LobbyRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixlobbyroomstatus(room, mucstate)
            for room in site.waitingRooms.getNotDestroyed():
                logger.warning("Re-joining waitingRoom '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, WaitingRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixwaitingroomstatus(room, mucstate)
            for room in site.simpleRooms.getNotDestroyed():
                logger.warning("Re-joining simpleRoom '%s'." % room.jid)
                jid = str2roomjid(room.jid)
                mucstate = self.joinMucRoom(site, jid, room.password, SimpleRoomHandler, rejoining=True)
                # FIXME: check if we are owner of the room again (otherwise log error) & reconfigure room if locked
                if mucstate:
                    self.fixsimpleroomstatus(room, mucstate)

    def fixroomstatus(self, room, mucstate):
        # Wait until all events are processed
        # i.e. until all presence stanzas are received so we can count
        # the number of users in the freshly re-joined rooms
        while self.stream.loop_iter(1):
            logger.debug("Looping until all pending events are processed.")

        logger.warning("Checking status for room '%s'." % room.jid)
        status = room.getStatus()
        logger.warning("Status is '%s' for room '%s'." % (status, room.jid))
        client_id = room.client_id
        staff_id = room.staff_id
        userexited = room.getCleanExit()
        nUsers = len(mucstate.users) - 1 # -1 for not counting the bot itself
        logger.info("There are %d users in '%s'." % (nUsers, room.jid))

        if status in ("available", "availableForInvitaton"):
            if staff_id:
                if client_id:
                    logger.critical("BUG: a client was send to this room while status was still 'available' or 'availableForInvitation'. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
                else:
                    if nUsers >= 2:
                        logger.error("BUG: two users in the room while only staff was expected. Room: '%s'." % room.jid)
                        room.setStatus("toDestroy")
                    elif nUsers == 1:
                        logger.warning("Fixing status to 'staffWaiting'. Room: '%s'." % room.jid)
                        room.setStatus("staffWaiting")
                    else: # nUsers == 0
                        logger.warning("Expected staff member not present anymore: to be destroyed. Room: '%s'." % (room.jid))
                        room.setStatus("toDestroy")
            else:
                if client_id:
                    logger.critical("BUG: a client was send to room while no staff ever was: to be destroyed. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
                else:
                    logger.info("Status is correct.")

        elif status in ("staffWaiting", "staffWaitingForInvitee"):
            if staff_id:
                if client_id:
                    if userexited:
                        if nUsers >= 2:
                            logger.error("Two users in the room while at least one has exited cleanly: to be destroyed. Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                        elif nUsers == 1:
                            logger.warning("Fixing status to 'closingChat'. A user has exited cleanly. Room: '%s'." % room.jid)
                            room.setStatus("closingChat")
                        else: # nUsers == 0
                            logger.warning("Both users seem to have left. At least one exited cleanly: to be destroyed Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                    else:
                        if nUsers >= 2:
                            logger.error("Fixing status to 'chatting'. Two users in the room now and client was send here. Room: '%s'." % room.jid)
                            room.setStatus("chatting")
                        elif nUsers == 1:
                            logger.warning("Fixing status to 'lost'. One user is missing. Room: '%s'." % room.jid)
                            room.setStatus("lost")
                        else: # nUsers == 0
                            logger.warning("Fixing status to 'abandoned'. Both users missing. Room: '%s'." % room.jid)
                            room.setStatus("abandoned")
                else: # no client_id
                    if nUsers >= 2:
                        logger.error("BUG: two users in the room while only staff was expected. Room: '%s'." % room.jid)
                        room.setStatus("toDestroy")
                    elif nUsers == 1:
                        logger.info("Status is correct.")
                    else: # nUsers == 0
                        logger.warning("Expected staff member not present anymore: to be destroyed. Room: '%s'." % room.jid)
                        room.setStatus("toDestroy")
            else: # no staff_id
                logger.critical("BUG: a staff member was never send here: to be destroyed. Room: '%s'." % room.jid)
                room.setStatus("toDestroy")

        elif status == "chatting":
            if staff_id:
                if client_id:
                    if userexited:
                        if nUsers >= 2:
                            logger.error("Two users in the room while at least one has exited cleanly: to be destroyed. Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                        elif nUsers == 1:
                            logger.info("One user left cleanly. Fixing status to 'closingChat'.")
                            room.setStatus("closingChat")
                        else: # nUsers == 0
                            logger.warning("Both users seem to have left. At least one exited cleanly: to be destroyed Room: '%s'." % room.jid)
                            room.setStatus("toDestroy")
                    else: # no clean exit
                        if nUsers >= 2:
                            logger.info("Status is correct.")
                        elif nUsers == 1:
                            logger.warning("Fixing status to 'lost'. One user is missing. Room: '%s'." % room.jid)
                            room.setStatus("lost")
                        else: # nUsers == 0
                            logger.warning("Fixing status to 'abandoned'. Both users missing. Room: '%s'." % room.jid)
                            room.setStatus("abandoned")
                else: # no client_id
                    logger.error("Status 'chatting' invalid since no client was ever send here. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
            else: # no staff_id
                logger.error("Status 'chatting' invalid since no staff member was ever send here. Room: '%s'." % room.jid)
                room.setStatus("toDestroy")

        elif status == 'closingChat':
            if nUsers >= 2:
                logger.error("Two users in room while status was already 'closingChat'. Room: '%s'." % room.jid)
                room.setStatus("toDestroy")
            elif nUsers == 1:
                logger.info("Status is correct.")
            else: # nUsers == 0
                logger.warning("No user left in room. To be destroyed. Room: '%s'." % room.jid)
                room.setStatus("abandoned")

        elif status == 'toDestroy':
            if nUsers >= 1:
                logger.error("Unexpected users in room: '%s'."  % room.jid)
                room.setStatus("toDestroy")
            else: # nUsers == 0
                logger.info("Status correct.")

        elif status == 'lost':
            if userexited:
                if nUsers >= 2:
                    logger.error("Unexpected user in room: '%s'."  % room.jid)
                    room.setStatus("toDestroy")
                elif nUsers == 1:
                    logger.warning("Only one user in room. Closing this chat. Room: '%s'." % room.jid)
                    room.setStatus("closingChat")
                else: # nUsers == 0
                    logger.warning("No user has returned. To be destroyed. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
            else:
                if nUsers >= 2:
                    logger.info("Both user returned to room. Fixing status to 'chatting'. Room: '%s'."  % room.jid)
                    room.setStatus("chatting")
                elif nUsers == 1:
                    logger.warning("Status is correct.")
                    room.setStatus("lost")
                else: # nUsers == 0
                    logger.warning("No user has returned. Fixing status to 'abandoned'. Room: '%s'." % room.jid)
                    room.setStatus("abandoned")

        elif status == 'abandoned':
            if userexited:
                if nUsers >= 2:
                    logger.error("Unexpected users in room: '%s'."  % room.jid)
                    room.setStatus("toDestroy")
                elif nUsers == 1:
                    logger.warning("Only one user returned. Closing this chat. Room: '%s'." % room.jid)
                    room.setStatus("closingChat")
                else: # nUsers == 0
                    logger.warning("No user has returned. To be destroyed. Room: '%s'." % room.jid)
                    room.setStatus("toDestroy")
            else:
                if nUsers >= 2:
                    logger.info("Both users returned to room. Fixing status to 'chatting'. Room: '%s'."  % room.jid)
                    room.setStatus("chatting")
                elif nUsers == 1:
                    logger.warning("One user has returned to room. Fixing status to 'lost'. Room: '%s'."  % room.jid)
                    room.setStatus("lost")
                else: # nUsers == 0
                    logger.warning("Status is correct.")
        # Finished fixing, set rejoinCount to None
        room.rejoinCount = None


    def fixgrouproomstatus(self, room, mucstate):
        # Wait until all events are processed
        # i.e. until all presence stanzas are received so we can count
        # the number of users in the freshly re-joined rooms
        while self.stream.loop_iter(1):
            logger.debug("Looping until all pending events are processed.")

        logger.warning("Checking status for group room '%s'." % room.jid)
        status = room.getStatus()
        logger.warning("Status is '%s' for group room '%s'." % (status, room.jid))
        chat_id = room.chat_id
        nUsers = len(mucstate.users) - 1 # -1 for not counting the bot itself
        logger.info("There are %d users in '%s'." % (nUsers, room.jid))

        if status in ("available"):
            if chat_id: # room has been assigned to a chat in meanwhile
                if nUsers >= 1:
                    logger.warning("Fixing status to 'chatting'. GroupRoom: '%s'." % room.jid)
                    room.setStatus("chatting")
                else: # nUsers == 0
                    logger.warning("Expected users not present: mark as abandoned. GroupRoom: '%s'." % room.jid)
                    room.setStatus("abandoned")

        elif status == "chatting":
            if chat_id:
                if nUsers >= 1:
                    logger.info("Status is correct.")
                else: # nUsers == 0
                    logger.warning("Fixing status to 'abandoned'. All users missing. GroupRoom: '%s'." % room.jid)
                    room.setStatus("abandoned")
            else: # no chat_id
                logger.error("Status 'chatting' invalid since no chat has been assigned. GroupRoom: '%s'." % room.jid)
                room.setStatus("toDestroy")

        elif status == 'abandoned':
            if nUsers >= 1:
                logger.info("User(s) returned to group room. Fixing status to 'chatting'. GroupRoom: '%s'."  % room.jid)
                room.setStatus("chatting")
            else: # nUsers == 0
                logger.warning("Status is correct.")
        # Finished fixing, set rejoinCount to None
        room.rejoinCount = None

    def fixlobbyroomstatus(self, room, mucstate):
        """ [TODO] """
        pass

    def fixwaitingroomstatus(self, room, mucstate):
        """ [TODO] """
        pass

    def fixsimpleroomstatus(self, room, mucstate):
        """ [TODO] """
        pass

    def joinMucRoom(self, site, jid, password, handlerClass, rejoining=False):
        mucconf = self.getMucSettings(site.name)
        nick = mucconf["nick"].strip() or self.nick
        muchandler = handlerClass(self, site, mucconf, nick, password, rejoining)
        logger.debug("MUC-room setting: history_maxchars=%s,  history_stanzas=%s, history_seconds=%s" % (
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
            logger.warning("Could not join room %s: %s" % (jid.as_string(), str(e)))
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
        logger.info("Kicking user with nick '%s'." % nick)
        xml = "<iq to='%s' type='set' id='kick123'><query xmlns='http://jabber.org/protocol/muc#admin'><item role='none' nick='%s'/></query></iq>" % (roomjid, nick)
        self.stream.write_raw(xml)

    def makeModerator(self, roomjid, nick):
        if isinstance(roomjid, str) or isinstance(roomjid, unicode):
            roomjid = str2roomjid(roomjid)
        logger.info("Making user with nick '%s' moderator." % nick)

        xml = "<iq to='%s' type='set' id='mod'><query xmlns='http://jabber.org/protocol/muc#admin'><item role='moderator' nick='%s'/></query></iq>" % (roomjid, nick)
        logger.debug(xml)
        self.stream.write_raw(xml)

    def sendInvite(self, room, to):
        xml = "<message to='%s'><x xmlns='http://jabber.org/protocol/muc#user'><invite to='%s'/></x></message>" % (room.jid, to)
        logger.info("sending invite: %s" % xml)
        self.stream.write_raw(xml)

    def inviteClients(self, waitingRoom):
        rooms = One2OneRoom.objects.filter(status='staffWaiting').order_by('status_timestamp')
        for room in rooms:
            client = waitingRoom.getNextClient()
            if not client is None:
                self.sendInvite(room, client.real_jid)
            else:
                # no more waiting clients
                break

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
            rooms = site.rooms.getNotDestroyed() + site.groupRooms.getNotDestroyed() + site.lobbyRooms.getNotDestroyed() + site.waitingRooms.getNotDestroyed() + site.simpleRooms.getNotDestroyed()
        else:
            rooms = site.rooms.getByStatus(roomstatus) + site.groupRooms.getByStatus(roomstatus) + site.lobbyRooms.getByStatus(roomstatus) + site.waitingRooms.getByStatus(roomstatus) + site.simpleROoms.getByStatus(roomstatus)
        for room in rooms:
            self.closeRoom(room)

    def closeRoom(self, room):
        roomjid = str2roomjid(room.jid)
        logger.info("Closing down MUC-room '%s'." % room.jid)
        roomstate = self.mucmanager.rooms[unicode(roomjid)]
        roomstate.handler.closingDown = True
        mynick = roomstate.get_nick()
        for nick in roomstate.users.iterkeys():
            if nick != mynick:
                self.kick(roomjid, nick)
        logger.info("Leaving MUC-room '%s'." % room.jid)
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
            int(self.conf.muc.poolsize)
        except ValueError:
            return "MUC-room pool size invalid"
        self.conf.muc.poolsize = newSize
        logger.info("MUC-room pool size set to %s" % newSize)
        self.todo.append((self.fillMucRoomPool,))
        return str()

    # XMPP handler methods
    #
    def handle_message(self, s):
        if s.get_type() == "headline":
            return True
        log_stanza(s)
        message = u"Don't call us. We call you.."
        msg = Message(None, s.get_to(), s.get_from(), s.get_type(), None, None, message)
        self.stream.send(msg)
        self.printrooms()
        return True

    def handle_iq_get_room(self, iq):
        log_stanza(iq)
        room = None
        try:
            try:
                token_n = iq.xpath_eval('d:query/d:token', {'d': NS_HELPIM_ROOMS})[0]
            except IndexError:
                raise BadRequestError()

            logger.info("token: %s" % token_n.getContent())

            ac = AccessToken.objects.get(token=token_n.getContent())
            logger.info("got accessToken: %s" % ac)

            """ save jid """
            ac.jid = iq.get_from()
            ac.save()

            try:
                self.handle_simple_room_token(iq, ac)
                return
            except SimpleRoomToken.DoesNotExist:
                pass

            resIq = iq.make_result_response()
            resIq.new_query(NS_HELPIM_ROOMS)

            if ac.role == Participant.ROLE_CLIENT:
                """ send invite to waiting room """
                logger.info("got a client, sending to waiting room")
                try:
                    room = WaitingRoom.objects.filter(status='chatting')[0]
                except IndexError:
                    room = WaitingRoom.objects.filter(status='abandoned')[0]
                if not room.lobbyroom or room.lobbyroom.getStatus() != 'chatting':
                    room.setStatus('toDestroy');
                    room = None
                    raise IndexError()

                try:
                    waitingRoomToken =  WaitingRoomToken.objects.get(token=ac)
                    waitingRoomToken.room = room
                    waitingRoomToken.save()
                except WaitingRoomToken.DoesNotExist:
                    WaitingRoomToken.objects.create(token=ac, room=room)

            else:
                logger.info("got token from staff member")
                """ first we try to find an already allocated room which has status 'chatting' """

                try:
                    room = LobbyRoomToken.objects.get(token=ac).room

                    """ staff has already acquired a lobby. now check
                    if he's really in there. if not send to room, send
                    to one2one room otherwise """
                    if not self.mucmanager.get_room_state(JID(room.jid)).get_user(iq.get_from()) is None:
                        if One2OneRoomToken.objects.filter(token=ac).filter(room__status__in=['staffWaiting', 'chatting']).count() < self.conf.muc.max_chats_per_staff:
                            logger.info("assigning new one2one room to token %s" % ac.token)
                            room = One2OneRoom.objects.filter(status='available')[0]
                            One2OneRoomToken.objects.create(token=ac, room=room)
                        else:
                            logger.info("user exceeded one2oneroom limit with token %s" % ac.token)
                            room = None
                            raise NotAllowedError()

                except (AttributeError, LobbyRoomToken.DoesNotExist, LobbyRoom.DoesNotExist):
                    try:
                        try:
                            """ just in case delete this bad ref """
                            LobbyRoomToken.objects.get(token=ac).delete()
                        except LobbyRoomToken.DoesNotExist:
                            pass
                        room = LobbyRoom.objects.filter(status='chatting')[0]
                    except IndexError:
                        try:
                            room = LobbyRoom.objects.filter(status='abandoned').order_by('pk')[0]
                        except IndexError:
                            room = LobbyRoom.objects.filter(status='available').order_by('pk')[0]
                    """ save token to lobby """
                    LobbyRoomToken.objects.create(token=ac, room=room)

        except AccessToken.DoesNotExist:
            logger.info("Bad AccessToken given: %s" % token_n.getContent())
            resIq = iq.make_error_response(u"not-authorized")
        except IndexError:
            """ is this the only index error that might appear? """
            logger.info("No available room found")
            resIq = iq.make_error_response(u"item-not-found")
        except BadRequestError:
            logger.info("request xml was malformed: %s" % iq.serialize())
            resIq = iq.make_error_response(u"bad-request")
        except NotAllowedError:
            logger.info("not allowed to join more rooms with token %s" % ac.token)
            resIq = iq.make_error_response(u"not-allowed")

        self.stream.send(resIq)
        if not room is None:
            self.sendInvite(room, iq.get_from())

    def handle_simple_room_token(self, iq, ac):
        simple_room_token = SimpleRoomToken.objects.get(token=ac)
        room = simple_room_token.room
        
        resIq = iq.make_result_response()
        resIq.new_query(NS_HELPIM_ROOMS)
        self.stream.send(resIq)
        self.sendInvite(room, iq.get_from())

    def handle_iq_get_conversationId(self, iq):
        log_stanza(iq)

        try:
            room_jid = iq.get_from().bare()
            room = One2OneRoom.objects.get(jid=room_jid)
            resIq = iq.make_result_response()
            query = resIq.new_query(NS_HELPIM_ROOMS)
            query.newChild(None, 'conversationId', '%s'%room.chat.pk)
        except:
            resIq = iq.make_error_response(u"item-not-found")

        self.stream.send(resIq)

    def handle_iq_set_block_participant(self, iq):

        """ [TODO] actually this should be connected to a room so that
        we know whether we are talking about a one2OneRoom or not """

        log_stanza(iq)

        try:
            try:
                iq.xpath_eval('d:block/d:participant', {'d': NS_HELPIM_ROOMS})[0]
            except IndexError:
                raise BadRequestError()

            logger.info("got block request from %s" % iq.get_from())
            from_jid = iq.get_from()

            room_jid = from_jid.bare()
            staff_nick = from_jid.resource

            """ get associated room - as of now this can only be a One2OneRoom (see above) """
            room = One2OneRoom.objects.get(jid=room_jid)

            """ first check if sender is a staff member """
            if room.staff_nick != staff_nick:
                raise NotAuthorizedError()

            client = Participant.objects.filter(conversation=room.chat).filter(role=Participant.ROLE_CLIENT)[0]
            client.blocked = True
            client.save()

            resIq = iq.make_result_response()
            resIq.new_query(NS_HELPIM_ROOMS)

        except One2OneRoom.DoesNotExist:
            resIq = iq.make_error_response(u"item-not-found")

        except NotAuthorizedError:
            resIq = iq.make_error_response(u"not-authorized")

        except BadRequestError:
            logger.info("request xml was malformed: %s" % iq.serialize())
            resIq = iq.make_error_response(u"bad-request")

        self.stream.send(resIq)

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

class BotError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class BadRequestError(Exception):
    def __init__(self, msg='bad request'):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class NotAuthorizedError(Exception):
    def __init__(self, msg='not authorized'):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class NotAllowedError(Exception):
    def __init__(self, msg='not allowed'):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class Stats:
    pass
