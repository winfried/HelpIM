from django.db import models
from django.contrib.auth.models import User

class Conversation(models.Model):
    start_time = models.DateTimeField()
    subject = models.CharField(max_length=64, blank=True)

    def __unicode__(self):
        return self.start_time.strftime('%c')

    class Meta:
        ordering = ['start_time']

class Participant(models.Model):
    conversation = models.ForeignKey(Conversation)
    name = models.CharField(max_length=64)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation)
    sender = models.ForeignKey(Participant)
    sender_name = models.CharField("participant's name when sending", max_length=64)
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
