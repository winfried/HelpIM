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
        Finds the variable class for the given name. Otherwise, returns NoneReportVariable.
        '''
        return cls.known_variables.get(name, NoneReportVariable)

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
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls):
        return [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday'), Report.OTHER_COLUMN]

class BranchReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuple(cls):
        return ('branch', _('Branch office'))

    @classmethod
    def extract_value(cls, obj):
        try:
            return obj.getStaff().user.additionaluserinformation.branch_office.name
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls):
        for office in BranchOffice.objects.all():
            yield office.name
        yield Report.OTHER_COLUMN

class NoneReportVariable(ReportVariable):
    '''
    Special kind of report variable that only has one bucket EMPTY and sorts every object into it.
    Used as a fallback when no variable is selected in the report.
    '''
    
    EMPTY = _('All')
    
    @classmethod
    def get_choices_tuple(cls):
        return ('none', _('None'))

    @classmethod
    def extract_value(cls, obj):
        return NoneReportVariable.EMPTY

    @classmethod
    def values(cls):
        yield NoneReportVariable.EMPTY
    
class Report(models.Model):
    VARIABLE_CHOICES = [ x.get_choices_tuple() for x in ReportVariable.all_variables() ]

    OUTPUT_CHOICES = (
        ('hits', _('Hits')),
        ('unique', _('Unique IPs'))
    )
    
    # special column names
    OTHER_COLUMN = _('No value')
    TOTAL_COLUMN = _('Total')

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

        # get Variable objects for variables selected in Report
        var1 = ReportVariable.find_variable(self.variable1)
        var2 = ReportVariable.find_variable(self.variable2)

        # find their possible values to use in row/column headings of table 
        var1_samples = list(var1.values())
        var2_samples = list(var2.values())

        # create table, extended by extra row and column for row/col/table sums
        data = defaultdict(dict)
        for val1, val2 in product(var1_samples + [Report.TOTAL_COLUMN], var2_samples + [Report.TOTAL_COLUMN]):
            data[val1][val2] = 0

        # fill inner cells
        for chat in self.matching_chats():
            var1_value = var1.extract_value(chat)

            if var2 is None:
                var2_value = Report.TOTAL_COLUMN
            else:
                var2_value = var2.extract_value(chat)

            data[var1_value][var2_value] += 1

        # calc row/col/table sums (outer cells)
        for val1, val2 in product(var1_samples, var2_samples):
            current = data[val1][val2]

            # add to: table sum, col sum, row sum
            data[Report.TOTAL_COLUMN][Report.TOTAL_COLUMN] += current
            data[val1][Report.TOTAL_COLUMN] += current
            data[Report.TOTAL_COLUMN][val2] += current

        return { 'rendered_report': data,
            'variable1_samples': var1_samples + [Report.TOTAL_COLUMN],
            'variable2_samples': var2_samples + [Report.TOTAL_COLUMN],
        }
