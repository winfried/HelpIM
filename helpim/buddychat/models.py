from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from registration.models import RegistrationProfile, RegistrationManager

from helpim.conversations.models import Conversation

class BuddyChatProfileManager(RegistrationManager):
    def create(self, user, activation_key):
        now = datetime.now()
        conv1 = Conversation(start_time=now)
        conv2 = Conversation(start_time=now)
        conv3 = Conversation(start_time=now)
        profile = BuddyChatProfile(
            user = user,
            activation_key = activation_key,
            careworker_conversation = conv1,
            coordinator_conversation = conv2,
            careworker_coordinator_conversation = conv3,
            )
        profile.save()
        return profile

class BuddyChatProfile(RegistrationProfile):

    ready = models.BooleanField(default=False)
    careworker = models.ForeignKey(User,
                                  verbose_name=_("Careworker"),
                                  blank=True,
                                  null=True,
                                  limit_choices_to = {'groups__name': 'volunteers'},
        )

    coupled_at = models.DateTimeField(blank=True, null=True)

    careworker_conversation = models.ForeignKey(Conversation)
    coordinator_conversation = models.ForeignKey(Conversation)
    careworker_coordinator_conversation = models.ForeignKey(Conversation)

    objects = BuddyChatProfileManager()

    class Meta:
        verbose_name = _("Chat Buddy")
        verbose_name_plural = _("Chat Buddies")
        permissions = (
            ('is_coordinator', 'Is allowed to coordinate careworkers and careseekers'),
            ('is_careworker', 'Is a careworker')
            )
