from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

class BranchOffice(models.Model):

    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _("Branch office")
        verbose_name_plural = _("Branch offices")

        permissions = (
            # Default: Can only view own conversations
            ("view_conversations_of_own_branch_office",
                _("View all conversations in own branch office")),

            ("view_conversations_of_all_branch_offices",
                _("View all conversations in all branch offices")),
        )

class AdditionalUserInformation(models.Model):
    def __unicode__(self):
        return _("Additional information about user %s" % self.user.username)

    class Meta:
        verbose_name = _("Additional user information")
        verbose_name_plural = _("Additional user information")

    user = models.OneToOneField(User, unique=True)

    branch_office = models.ForeignKey(BranchOffice, null=True, blank=True)

    chat_nick = models.CharField(_("Chatname"), max_length=64, blank=True)

class AdministrativeUser(User):
    """
    More restrictive view on User. See corresponding ModelAdmin for details. 
    """
    class Meta:
        app_label = 'auth'
        proxy = True

class BranchUser(User):
    """
    More restrictive view on User. See corresponding ModelAdmin for details.
    """
    class Meta:
        app_label = 'auth'
        proxy = True

class EventLogManager(models.Manager):
    def findByYearAndTypes(self, year, types):
        return self.filter(created_at__year=year, type__in=types).order_by('session', 'created_at')
    
class EventLog(models.Model):
    def __unicode__(self):
        return _('Event %(event_name)s at %(timestamp)s' % {'event_name': self.type, 'timestamp': self.created_at.strftime('%c')})

    objects = EventLogManager()
    
    created_at = models.DateTimeField(auto_now_add=True)

    type = models.CharField(max_length=255)

    session = models.CharField(max_length=255)

    payload = models.TextField(blank=True, null=True)

POSITION_CHOICES = [
  ('CB', _('Client, before chat')),
  ('CA', _('Client, after chat')),
  ('SA', _('Staff, after chat')),
  ('SC', _('Staff, on Conversation page')),
]

def get_position_choices():
    return POSITION_CHOICES

def register_position_choices(choices):
    global POSITION_CHOICES
    POSITION_CHOICES = choices
