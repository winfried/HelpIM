from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from helpim.conversations.models import Conversation, Participant

class Group(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()
    created_by = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    max_members = models.SmallIntegerField()
    is_open = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = _("Chatgroups")
        verbose_name = _("Chatgroup")

class Member(models.Model):
    group = models.ForeignKey(Group)
    email = models.EmailField()
    name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    invite_sent = models.BooleanField()
    is_admin = models.BooleanField()
    access_token = models.CharField(max_length=16)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['created_at']

class Meeting(Conversation):
    group = models.ForeignKey(Group)
    invites_sent = models.BooleanField()

class MeetingParticipant(Participant):
    meeting = models.ForeignKey(Meeting)
    member = models.ForeignKey(Member)
    is_admin = models.BooleanField()
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField()
