from django.db import models

from helpim.conversations.models import Chat, Participant
from django.utils.translation import ugettext as _

class GroupRoom(models.Model):
    STATUS_CHOICES = (
        ('AV', _('Available')),
        ('AI', _('Available for Invitation')),
        ('SW', _('Staff Waiting')),
        ('SI', _('Staff Waiting for Invitee')),
        ('CH', _('Chatting')),
        ('CL', _('Closing Chat')),
        ('TD', _('To Destroy')),
        ('DE', _('Destroyed')),
        ('LO', _('Lost')),
        ('AB', _('Abandoned')),
        )
    jid = models.CharField(max_length=255,
                           unique=True)
    password = models.CharField(max_length=64)
    status = models.CharField(max_length=2,
                              choices=STATUS_CHOICES)
    chat = models.ForeignKey(Chat)
    web_clean_exit = models.BooleanField()
    status_timestamp = models.DateTimeField()
    modified_timestamp = models.DateTimeField()

class One2OneRoom(GroupRoom):
    staff_id = models.ForeignKey(Participant)
    staff_nick = models.CharField(max_length=64)
    client_id = models.CharField(max_length=64)
    client_nick = models.CharField(max_length=64)
