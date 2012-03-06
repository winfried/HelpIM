from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from helpim.common.models import BranchOffice


class Report(models.Model):
    title = models.CharField(max_length=255)

    period_start = models.DateField()
    period_end = models.DateField()

    # staff user in chat
    branch = models.ForeignKey(BranchOffice,
        verbose_name=_('Branch office')
    )
    careworker = models.ForeignKey(User,
        verbose_name=_('Careworker'),
        limit_choices_to={ 'groups__name': 'careworkers' },
    )

    # filter by properties of chat
    filter_none = models.BooleanField()
    filter_business_hours = models.BooleanField()
    filter_blocked = models.BooleanField()
    filter_queued = models.BooleanField()
    filter_assigned = models.BooleanField()
    filter_interactive = models.BooleanField()

    # what to show in result
    variable1 = models.CharField(max_length=255)
    variable2 = models.CharField(max_length=255)
    output = models.CharField(max_length=255)
