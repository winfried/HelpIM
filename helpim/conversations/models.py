from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from threadedcomments.models import ThreadedComment

from helpim.questionnaire.models import ConversationFormEntry


class ConversationManager(models.Manager):
    def getConversationYears(self):
        """Returns list with years and number of Conversations during year"""

        # see: https://code.djangoproject.com/ticket/10302
        extra_mysql = {"year": "YEAR(start_time)"}
        return Conversation.objects.extra(select=extra_mysql).values("year").annotate(count=models.Count('id')).order_by('start_time')

    def getConversations(self, whichYear):
        """Returns Conversations of year specified"""
        return Conversation.objects.filter(start_time__year=whichYear).extra(select={"hourAgg": "LEFT(start_time, 13)"}).order_by('start_time')

class Conversation(models.Model):
    start_time = models.DateTimeField()
    subject = models.CharField(max_length=64, blank=True)

    objects = ConversationManager()

    def __unicode__(self):
        return _('"%(subject)s" at %(start_time)s') % {
          'subject': self.subject,
          'start_time': self.start_time.strftime('%c'),
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
            
    def client_nickname(self):
        try:
            return Participant.objects.filter(conversation=self,role=Participant.ROLE_CLIENT)[0].name
        except:
            return _('(None)')

    def staff_nickname(self):
        try:
            return Participant.objects.filter(conversation=self,role=Participant.ROLE_STAFF)[0].name
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
        
    def waitingTime(self):
        # TODO: what if no questionnaire was issued?
        
        try:
            # when was questionnaire submitted?
            formEntry = ConversationFormEntry.objects.filter(conversation=self, position='CB')[0].entry
            
            # when did client Participant join?
            firstMessage = Message.objects.filter(conversation=self,sender__role=Participant.ROLE_CLIENT).order_by('created_at')[0]
            
            return int((firstMessage.created_at - formEntry.entry_time).total_seconds())
        except IndexError:
            return 0

    def hasQuestionnaire(self, pos='CB'):
        """Returns whether Questionnaire at given position was submitted for this Conversation"""
        return bool(ConversationFormEntry.objects.filter(conversation=self, position=pos, entry__isnull=False).count())
    
    def hasInteraction(self):
        """Returns true if both client and staff Participants chatted during this Conversation"""
        clientChatted = Message.objects.filter(conversation=self,sender__role=Participant.ROLE_CLIENT).exclude(body__exact='').count() > 0
        staffChatted = Message.objects.filter(conversation=self,sender__role=Participant.ROLE_STAFF).exclude(body__exact='').count() > 0
        
        return clientChatted and staffChatted

    class Meta:
        ordering = ['start_time']
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

    def save(self, *args, **kwargs):
        if self.blocked:
            self.blocked_at = datetime.now()
        super(Participant, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")

class Message(models.Model):
    conversation = models.ForeignKey(Conversation)
    sender = models.ForeignKey(Participant)
    sender_name = models.CharField(_("Sender"), max_length=64)
    created_at = models.DateTimeField()
    body = models.TextField()

    comments = models.ManyToManyField(ThreadedComment)

    def time_sent(self):
        return str(self.created_at.time())

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.now()
        super(Message, self).save(*args, **kwargs)


class Chat(Conversation):
    pass

class ChatMessage(Message):
    EVENT_CHOICES = (
        ('message', _('Chat message')),
        ('join', _('Chat joining')),
        ('rejoin', _('Chat rejoining')),
        ('left', _('Chat exit')),
        ('ended', _('Chat end')),
    )
    event = models.CharField(max_length=10, choices=EVENT_CHOICES, default='message')
