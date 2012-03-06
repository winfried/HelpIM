from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from helpim.common.models import BranchOffice


class Report(models.Model):
    VARIABLE_CHOICES = (
        ('branch', _('Branch office')),
        ('weekday', _('Weekday')),
    )

    OUTPUT_CHOICES = (
        ('hits', _('Hits')),
        ('unique', _('Unique IPs'))
    )

    title = models.CharField(max_length=255)

    period_start = models.DateField()
    period_end = models.DateField()

    # staff user in chat
    branch = models.ForeignKey(BranchOffice, null=True, related_name='+',
        verbose_name=_('Branch office'),
    )
    careworker = models.ForeignKey(User, null=True, related_name='+',
        verbose_name=_('Careworker'),
        limit_choices_to={ 'groups__name': 'careworkers' },
    )

    # filter by properties of chat
    filter_none = models.BooleanField(verbose_name=_('Show all'))
    filter_business_hours = models.BooleanField(verbose_name=_('Hits outside of business hours'))
    filter_blocked = models.BooleanField(verbose_name=_('Hits from blocked IPs'))
    filter_queued = models.BooleanField(verbose_name=_('Hits when waiting queue was full'))
    filter_assigned = models.BooleanField(verbose_name=_('Assigned chats'))
    filter_interactive = models.BooleanField(verbose_name=_('Interactive chats'))

    # what to show in result
    variable1 = models.CharField(max_length=255, choices=VARIABLE_CHOICES,
        verbose_name=_('select row variable'),
    )
    variable2 = models.CharField(max_length=255, choices=VARIABLE_CHOICES,
        verbose_name=_('select column variable')
    )
    output = models.CharField(max_length=255, choices=OUTPUT_CHOICES, default=OUTPUT_CHOICES[0],
        verbose_name=_('select information to show')
    )
