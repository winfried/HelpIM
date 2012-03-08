from collections import defaultdict
from datetime import datetime, time
from itertools import product

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext as _

from helpim.common.models import BranchOffice
from helpim.conversations.models import Chat, Participant

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

    # leave blank to indicate no lower bound
    period_start = models.DateField(null=True, blank=True,
        verbose_name=_('Chats from (inclusive)')
    )
    
    # leave blank to indicate no upper bound
    period_end = models.DateField(null=True, blank=True,
        verbose_name=_('Chats until (inclusive)')
    )

    # staff user in chat
    branch = models.ForeignKey(BranchOffice, null=True, blank=True, related_name='+',
        verbose_name=_('Branch office'),
    )
    careworker = models.ForeignKey(User, null=True, blank=True, related_name='+',
        verbose_name=_('Careworker'),
        limit_choices_to={ 'groups__name': 'careworkers' },
    )

    # filter by properties of chat
    filter_none = models.BooleanField(default=True, verbose_name=_('Show all'))
    filter_business_hours = models.BooleanField(verbose_name=_('Hits outside of business hours'))
    filter_blocked = models.BooleanField(verbose_name=_('Hits from blocked IPs'))
    filter_queued = models.BooleanField(verbose_name=_('Hits when waiting queue was full'))
    filter_assigned = models.BooleanField(verbose_name=_('Assigned chats'))
    filter_interactive = models.BooleanField(verbose_name=_('Interactive chats'))

    # what to show in result
    variable1 = models.CharField(max_length=255, choices=VARIABLE_CHOICES,
        verbose_name=_('select row variable'),
    )
    variable2 = models.CharField(max_length=255, choices=VARIABLE_CHOICES, null=True, blank=True,
        verbose_name=_('select column variable')
    )
    output = models.CharField(max_length=255, choices=OUTPUT_CHOICES, default=OUTPUT_CHOICES[0],
        verbose_name=_('select information to show')
    )

    def get_absolute_url(self):
        return reverse('report_show', args=[self.id])
    
    def __unicode__(self):
        return self.title

    def matching_chats(self):
        '''
        Returns a QuerySet for Chat objects that match the following criteria as specified in this Report:
          - `period_start`
          - `period_end`
          - `branch`
          - `careworker`
        '''

        chat_query = Chat.objects.all()

        if not self.period_start is None:
            chat_query = chat_query.filter(start_time__gte=datetime.combine(self.period_start, time.min))
        if not self.period_end is None:
            chat_query = chat_query.filter(start_time__lte=datetime.combine(self.period_end, time.max))

        if not self.branch is None:
            chat_query = chat_query.filter(participant__user__additionaluserinformation__branch_office=self.branch)

        if not self.careworker is None:
            chat_query = chat_query.filter(participant__user=self.careworker, participant__role=Participant.ROLE_STAFF)

        return chat_query

    def generate(self):
        '''
        Generates the data for the report. Returns a dictionary that can be directly added to the view's context.
        '''
        
        data = defaultdict(dict)
        
        var1_samples = self.variable_samples(self.variable1)
        var2_samples = self.variable_samples(self.variable2)
        
        for var1, var2 in product(var1_samples, var2_samples):
            data[var1][var2] = 0
        
        for chat in self.matching_chats():
            pass
        
        return { 'rendered_report': data,
            'variable1_samples': var1_samples,
            'variable2_samples': var2_samples,
        }
    
    def variable_samples(self, var_name):
        '''
        Returns a list with all values the given variable `var_name` can have.
        '''
        
        if var_name is None:
            return [_('Total')]
        
        appendix = [_('Other'), _('Total')]
        
        if var_name == 'branch':
            return [] + appendix
        elif var_name == 'weekday':
            return [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday'), ] + appendix