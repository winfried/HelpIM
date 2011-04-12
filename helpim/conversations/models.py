from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

class Conversation(models.Model):
    start_time = models.DateTimeField()
    subject = models.CharField(max_length=64, blank=True)

    def __unicode__(self):
        return _('"%(subject)s" at %(start_time)s') % {
          'subject': self.subject,
          'start_time': self.start_time.strftime('%c'),
        }

    class Meta:
        ordering = ['start_time']
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")

class Participant(models.Model):
    ROLE_CHOICES = (
        ('CS', _('Care seeker')),
        ('CW', _('Care worker')),
    )

    conversation = models.ForeignKey(Conversation)
    name = models.CharField(max_length=64)

    role = models.CharField(max_length=2, choices=ROLE_CHOICES, null=True)

    class Meta:
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")

class Message(models.Model):
    conversation = models.ForeignKey(Conversation)
    sender = models.ForeignKey(Participant)
    sender_name = models.CharField(_("Participant's name at sending time"), max_length=64)
    created_at = models.DateTimeField()
    body = models.TextField()

class MessageComment(models.Model):
    parent = models.ForeignKey('self')
    message = models.ForeignKey(Message)
    author = models.ForeignKey(User)
    created_at = models.DateTimeField()
    body = models.TextField()

class Chat(Conversation):
    room = models.IntegerField()

class ChatMessage(Message):
    pass
