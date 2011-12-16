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

    objects = RegistrationManager()

    class Meta:
        verbose_name = _("Chat Buddy")
        verbose_name_plural = _("Chat Buddies")

    def couple(self, volunteer=None):
        # TODO raise an exception if volunteer is not a volunteer
        self.volunteer = volunteer
        self.save()
        return self

    def decouple(self):
        return self.couple()

