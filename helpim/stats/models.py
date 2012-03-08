from collections import defaultdict
from datetime import datetime, time
from itertools import chain, product

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext as _

from helpim.common.models import BranchOffice
from helpim.conversations.models import Chat, Participant


class ReportVariable(object):
    known_variables = {}

    @classmethod
    def all_variables(cls):
        '''
        Returns iterator over all known variables.
        When this is called for the first time, will auto-register direct subclasses.
        '''
        if len(cls.known_variables) == 0:
            # autodiscover and add direct subclasses
            for subcls in cls.__subclasses__():
                cls._register_variable(subcls)

        return cls.known_variables.itervalues()

    @classmethod
    def find_variable(cls, name):
        '''
        Finds the variable class for the given name. Otherwise, returns None.
        '''
        return cls.known_variables.get(name, None)

    @classmethod
    def _register_variable(cls, var):
        cls.known_variables[var.get_choices_tuple()[0]] = var

    @classmethod
    def get_choices_tuple(cls):
        '''
        Returns a 2-tuple consisting of an internal and public name for this variable.
        This tuple is used with django's `choices`-feature of model classes.
        '''
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def extract_value(cls, obj):
        '''
        Return the value for this variable in the context of the given object. 
        '''
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def values(cls):
        '''
        Return a list of values this variable can have.
        '''
        raise NotImplementedError("Subclass should implement this method.")

class WeekdayReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuple(cls):
        return ('weekday', _('Weekday'))

    @classmethod
    def extract_value(cls, obj):
        try:
            return cls.values()[obj.start_time.weekday()]
        except:
            return _('Other')

    @classmethod
    def values(cls):
        return [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday')]

class BranchReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuple(cls):
        return ('branch', _('Branch office'))

    @classmethod
    def extract_value(cls, obj):
        try:
            return obj.getStaff().user.additionaluserinformation.branch_office.name
        except:
            return _('Other')

    @classmethod
    def values(cls):
        for office in BranchOffice.objects.all():
            yield office.name


class Report(models.Model):
    VARIABLE_CHOICES = [ x.get_choices_tuple() for x in ReportVariable.all_variables() ]

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

        var1_samples = self.variable1_samples()
        var2_samples = self.variable2_samples()
        
        for var1, var2 in product(var1_samples, var2_samples):
            data[var1][var2] = 0

        for chat in self.matching_chats():
            pass

        return { 'rendered_report': data,
            'variable1_samples': var1_samples,
            'variable2_samples': var2_samples,
        }

    def variable1_samples(self):
        ''' shortcut method '''
        return self.variable_samples(self.variable1)

    def variable2_samples(self):
        ''' shortcut method '''
        return self.variable_samples(self.variable2)

    def variable_samples(self, var_name):
        '''
        Returns a list with all values the given variable `var_name` can have.
        '''

        # in case only first variable is selected and second is blank
        if var_name is None:
            return [_('Total')]

        # additional buckets that will be appended to variable samples
        appendix = [_('Other'), _('Total')]

        # lookup variable in registered variables
        # 
        var = ReportVariable.find_variable(var_name)
        if not var is None:
            return chain(var.values(), appendix)
        else:
            return appendix
