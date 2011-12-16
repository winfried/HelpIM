from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from registration.models import RegistrationProfile, RegistrationManager

class BuddyChatProfile(RegistrationProfile):

    ready = models.BooleanField(default=False)
    volunteer = models.ForeignKey(User,
                                  verbose_name=_("Volunteer"),
                                  blank=True,
                                  null=True,
                                  limit_choices_to = {'is_staff': True},
        )

    coupled_at = models.DateTimeField(blank=True, null=True)

    objects = RegistrationManager()

    class Meta:
        verbose_name = _("Chat Buddy")
        verbose_name_plural = _("Chat Buddies")
