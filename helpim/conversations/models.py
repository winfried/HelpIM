from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from threadedcomments.models import ThreadedComment


class Conversation(models.Model):
    created_at = models.DateTimeField()
    subject = models.CharField(max_length=64, blank=True)

    def __unicode__(self):
        return _('"%(subject)s" at %(created_at)s') % {
          'subject': self.subject,
          'created_at': self.created_at.strftime('%c'),
        }

    def getClient(self):
        """Returns assigned client Participant for this Conversation"""
        try:
            return Participant.objects.filter(conversation=self,role=Participant.ROLE_CLIENT)[0]
        except:
            None
    
    def getStaff(self):
        """Returns assigned staff member Participant for this Conversation"""
        try:
            return Participant.objects.filter(conversation=self,role=Participant.ROLE_STAFF)[0]
        except:
            None

    def get_participant(self, user):
        try:
            return Participant.objects.filter(conversation=self, user=user)[0]
        except:
            None

    def get_or_create_participant(self, user):
        participant = self.get_participant(user)
        if participant is None:
            participant = Participant.objects.create(conversation=self, name=user.username, user=user)
        return participant

    def client_name(self):
        '''Returns the client's nickname'''
        
        try:
            return Participant.objects.filter(conversation=self,role=Participant.ROLE_CLIENT)[0].name
        except:
            return _('(None)')

    def staff_name(self):
        '''Returns (in this order) either the staff members's realname, username or nickname; whichever is available'''
        
        try:
            participant = Participant.objects.filter(conversation=self,role=Participant.ROLE_STAFF)[0]
            
            if not participant.user is None:
                if participant.user.first_name or participant.user.last_name:
                    # strip() because one of the parts might be empty
                    return (_('%(first_name)s %(last_name)s') % {'first_name': participant.user.first_name, 'last_name': participant.user.last_name}).strip()
                if participant.user.username:
                    return participant.user.username
            
            # fallback: staff member's nickname
            return participant.name
        except:
            return _('(None)')

    def duration(self):
        # duration is defined as time between first and last real
        # message sent. a real message must contain a body
        messages = Message.objects.filter(conversation=self).exclude(body__exact='').order_by('created_at')
        try:
            return messages[len(messages)-1].created_at - messages[0].created_at
        except:
            return _('(unknown)')

    class Meta:
        ordering = ['created_at']
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")

class Participant(models.Model):

    ROLE_CLIENT = 'C'
    ROLE_STAFF = 'S'

    conversation = models.ForeignKey(Conversation)
    name = models.CharField(max_length=64)

    user = models.ForeignKey(User, null=True)

    role = models.CharField(max_length=2, choices=(
      (ROLE_CLIENT, _('Client')),
      (ROLE_STAFF, _('Staff')),
    ), null=True)

    ip_hash = models.CharField(max_length=32, blank=True)
    blocked = models.BooleanField()
    blocked_at = models.DateTimeField(null=True, default=None)

    def save(self, keep_blocked_at=False, *args, **kwargs):
        # dont always overwrite blocked_at with $now, necessary for importing data
        if self.blocked and not keep_blocked_at:
            self.blocked_at = datetime.now()
        super(Participant, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")

class BlockedParticipant(Participant):
    '''
    Using model proxies makes it possible to have a specialized ModelAdmin to display blocked Participants where verbose_name and ordering can be overridden without affecting Participant
    This also generates the usual set of *_blockedparticipant rights.
    
    Assign the 'change_blockedparticipant' right to any user/role that is allowed to unblock clients
    '''

    class Meta:
        proxy = True
        verbose_name = _('Blocked client')
        verbose_name_plural = _('Blocked clients')
        ordering = ['-blocked_at']

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages')
    sender = models.ForeignKey(Participant)
    sender_name = models.CharField(_("Sender"), max_length=64)
    created_at = models.DateTimeField()
    body = models.TextField()
    read = models.BooleanField(default=False)

    comments = models.ManyToManyField(ThreadedComment)

    def time_sent(self):
        return str(self.created_at.time())

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.now()
        super(Message, self).save(*args, **kwargs)


class Chat(Conversation):
    _waiting_time = None
    
    def hasQuestionnaire(self, pos='CB'):
        """Returns whether Questionnaire at given position was submitted for this Chat"""
        
        # conversationformentry_set manager only present when questionnaire app loaded
        if hasattr(self, 'conversationformentry_set'):
            return bool(self.conversationformentry_set.filter(position=pos,entry__isnull=False).count())
        else:
            return False
    
    def hasInteraction(self):
        """Returns true if both client and staff Participants chatted during this Chat"""
        clientChatted = ChatMessage.objects.filter(conversation=self,sender__role=Participant.ROLE_CLIENT,event='message').exclude(body__exact='').count() > 0
        staffChatted = ChatMessage.objects.filter(conversation=self,sender__role=Participant.ROLE_STAFF,event='message').exclude(body__exact='').count() > 0
        
        return clientChatted and staffChatted

    def was_queued(self):
        '''
        Returns a bool value indicating whether the careseeker in this Chat was sent to the waiting list.
        Returns None if it couldn't be determined (via common.EventLog).
        '''

        # avoid circular imports
        from helpim.conversations.stats import WaitingTimeFilter

        waiting_time = self.waiting_time()

        if waiting_time is None:
            return None
        elif waiting_time > WaitingTimeFilter.QUEUED_THRESHOLD:
            return True
        else:
            return False

    def waiting_time(self):
        """
        Returns waiting time in seconds for this Chat.
        Returns None, if it couldn't be determined (via common.EventLog).
        """

        if self._waiting_time is None:
            # avoid circular imports
            from helpim.common.models import EventLog
            from helpim.conversations.stats import EventLogProcessor, WaitingTimeFlatFilter

            result = {str(self.id): {'avgWaitTime': None, 'queued': 0}}

            # TODO: requiring session events to be within 1 hour isnt ideal
            # get all EventLogs for the session which yielded this Chat
            session_events = EventLog.objects.raw('''
                select e2.*
                from common_eventlog e1
                inner join common_eventlog e2
                    ON e1.session = e2.session AND ABS(TIMEDIFF(e1.created_at, e2.created_at) <= 3600)
                where e1.payload='%s'
                    AND e2.type IN ('helpim.rooms.waitingroom.joined', 'helpim.rooms.waitingroom.left', 'helpim.rooms.one2one.client_joined')
            ''', [self.id])
            EventLogProcessor(session_events, [WaitingTimeFlatFilter()]).run(result)

            self._waiting_time = result[str(self.id)]['avgWaitTime']

        return self._waiting_time

class ChatMessage(Message):
    EVENT_CHOICES = (
        ('message', _('Chat message')),
        ('join', _('Chat joining')),
        ('rejoin', _('Chat rejoining')),
        ('left', _('Chat exit')),
        ('ended', _('Chat end')),
    )
    event = models.CharField(max_length=10, choices=EVENT_CHOICES, default='message')
