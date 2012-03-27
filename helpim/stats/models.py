from collections import defaultdict
from datetime import datetime, time
from itertools import product

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.utils import DatabaseError
from django.utils.translation import ugettext as _

from forms_builder.forms.models import Field, FieldEntry

from helpim.common.models import BranchOffice
from helpim.conversations.models import Chat, Participant
from helpim.utils import total_seconds


class ReportVariable(object):
    known_variables = {}

    @classmethod
    def all_variables(cls):
        '''
        Returns iterator over all known distinct variables.
        When this is called for the first time, will auto-register direct subclasses.
        '''
        if len(cls.known_variables) == 0:
            # autodiscover and add direct subclasses
            for subcls in cls.__subclasses__():
                cls._register_variable(subcls)

        return set(cls.known_variables.itervalues())

    @classmethod
    def find_variable(cls, name):
        '''
        Finds the variable class for the given name. Otherwise, returns NoneReportVariable.
        '''
        return cls.known_variables.get(name, NoneReportVariable)

    @classmethod
    def _register_variable(cls, var):
        for choice in var.get_choices_tuples():
            cls.known_variables[choice[0]] = var

    @classmethod
    def get_choices_tuples(cls):
        '''
        Returns a list of 2-tuples consisting of an internal and public name for this variable.
        These tuples are used with django's `choices`-feature of model classes.
        '''
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def create_context(cls, choice_name):
        """
        Variable can create a context here that is later passed to extract_value() and values().
        `choice_name` is one of the names of a choice as returned by the variable's get_choices_tuples() method.
        """
        return None
    
    @classmethod
    def extract_value(cls, obj, context=None):
        '''
        Return the value for this variable in the context of the given object. 
        '''
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def values(cls, context=None):
        '''
        Return a list of values this variable can have.
        '''
        raise NotImplementedError("Subclass should implement this method.")

class HourReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuples(cls):
        return [('hour', _('Hour'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            return obj.start_time.hour
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        return range(0, 24) + [Report.OTHER_COLUMN]

class WeekdayReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuples(cls):
        return [('weekday', _('Weekday'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            return cls.values()[obj.start_time.weekday()]
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        return [_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday'), Report.OTHER_COLUMN]

class MonthReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuples(cls):
        return [('month', _('Month'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            return cls.values()[obj.start_time.month - 1]
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        return [_('January'), _('February'), _('March'), _('April'), _('May'), _('June'), _('July'), _('August'), _('September'), _('October'), _('November'), _('December'), Report.OTHER_COLUMN]

class BranchReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuples(cls):
        return [('branch', _('Branch office'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            return obj.getStaff().user.additionaluserinformation.branch_office.name
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        for office in BranchOffice.objects.values('name').distinct():
            yield office['name']
        yield Report.OTHER_COLUMN

class CareworkerReportVariable(ReportVariable):
    '''
    Regards only users who belong to 'careworker' group. All other users will go to `OTHER_COLUMN`
    '''

    @classmethod
    def get_choices_tuples(cls):
        return [('careworker', _('Careworker'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            careworker = obj.getStaff().user

            # is `careworker` user object in group 'careworker'?
            if careworker.groups.filter(name='careworkers').count() > 0:
                return careworker.username
            else:
                return Report.OTHER_COLUMN
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        for careworker in User.objects.filter(groups__name='careworkers').all():
            yield careworker.username
        yield Report.OTHER_COLUMN

class DurationReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuples(cls):
        return [('duration', _('Duration of chat'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            duration_minutes = total_seconds(obj.duration()) / 60.0

            if duration_minutes >= 0 and duration_minutes < 5.0:
                return _('0-5')
            elif duration_minutes >= 5.0 and duration_minutes < 10.0:
                return _('5-10')
            elif duration_minutes >= 10.0 and duration_minutes < 15.0:
                return _('10-15')
            elif duration_minutes >= 15.0 and duration_minutes < 25.0:
                return _('15-25')
            elif duration_minutes >= 25.0 and duration_minutes < 45.0:
                return _('25-45')
            elif duration_minutes >= 45.0:
                return _('45+')
            else:
                return Report.OTHER_COLUMN
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        return [_('0-5'), _('5-10'), _('10-15'), _('15-25'), _('25-45'), _('45+'), Report.OTHER_COLUMN]

class ConversationFormsReportVariable(ReportVariable):
    @classmethod
    def get_choices_tuples(cls):
        '''
        Return all questions in each questionnaire that has to do with conversations app (via questionnaire_conversationformentry relation).
        '''

        try :
            for question in Field.objects.filter(form__questionnaire__position__in=['CB', 'CA', 'SA', 'SC']).values('pk', 'label', 'form__title').order_by("form__id"):
                yield ('questionnaire-field-%s' % (question['pk']), _('Question: %(question)s on: %(form)s') % { 'form': question['form__title'], 'question': question['label'] })
        except DatabaseError:
            # will fail during 'syncdb' with 'table doesnt exist'
            pass

    @classmethod
    def create_context(cls, choice_name):
        '''
        returns the pk of the Field which this variable will analyze
        '''
        return int(choice_name.split('-')[2])

    @classmethod
    def extract_value(cls, obj, context=None):
        try:
            # for the current conversation, find the questionnaire that was sent with it that has an answer to the chosen question. retun this answer
            # "give me the answer to question `context` in questionnaire related to conversation `obj`?"
            return FieldEntry.objects.filter(field_id=context).filter(entry__conversationformentry__conversation=obj).values("value")[0]['value']
        except:
            return Report.OTHER_COLUMN

    @classmethod
    def values(cls, context=None):
        '''
        Return all given answeres to selected question
        '''

        # iterate all answers to selected question
        for answer in FieldEntry.objects.filter(field_id=context).values("value").distinct().order_by("value"):
            yield answer['value']

        yield Report.OTHER_COLUMN

class NoneReportVariable(ReportVariable):
    '''
    Special kind of report variable that only has one bucket EMPTY and sorts every object into it.
    Used as a fallback when no variable is selected in the report.
    '''

    EMPTY = _('All')

    @classmethod
    def get_choices_tuples(cls):
        return [('none', _('None'))]

    @classmethod
    def extract_value(cls, obj, context=None):
        return NoneReportVariable.EMPTY

    @classmethod
    def values(cls, context=None):
        yield NoneReportVariable.EMPTY

class Report(models.Model):
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
    filter_blocked = models.BooleanField(verbose_name=_('Hits from blocked IPs'))
    filter_queued = models.BooleanField(verbose_name=_('Hits that were queued'))
    filter_assigned = models.BooleanField(verbose_name=_('Assigned chats'))
    filter_interactive = models.BooleanField(verbose_name=_('Interactive chats'))

    # what to show in result
    variable1 = models.CharField(max_length=255,
        default=NoneReportVariable.get_choices_tuples()[0][0],
        verbose_name=_('select column variable'),
    )
    variable2 = models.CharField(max_length=255,
        default=NoneReportVariable.get_choices_tuples()[0][0],
        verbose_name=_('select row variable')
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
        Returns an iterator for Chat objects that match the following criteria as specified in this Report:
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

        # only return chats that match checkbox-filters
        for chat in chat_query.all():
            if self.apply_filters(chat):
                yield chat

    def apply_filters(self, chat):
        '''
        Only returns True if `chat` fulfills all checkbox filters and should be regarded in calculation.
        '''

        clientParticipant = chat.getClient()
        staffParticipant = chat.getStaff()

        if self.filter_blocked and (not clientParticipant is None and clientParticipant.blocked):
            return False
        if self.filter_queued and (not chat.was_queued()):
            return False
        if self.filter_assigned and (staffParticipant is None or clientParticipant is None):
            return False
        if self.filter_interactive and not chat.hasInteraction():
            return False

        return True

    def generate(self):
        '''
        Generates the data for the report. Returns a dictionary that can be directly added to the view's context.
        '''

        # get Variable objects for variables selected in Report
        var1 = ReportVariable.find_variable(self.variable1)
        var2 = ReportVariable.find_variable(self.variable2)

        var1_context = var1.create_context(self.variable1)
        var2_context = var2.create_context(self.variable2)

        # find their possible values to use in row/column headings of table 
        var1_samples = list(var1.values(var1_context))
        var2_samples = list(var2.values(var2_context))

        # how to init, update and produce result of cells depends on output mode of report
        if self.output == 'unique':
            # set-based, unique, looking at ip_hash of client
            init_cell = lambda: set()
            update_cell = lambda total, chat: total.add(chat.getClient().ip_hash) or total
            reduce_cell = lambda x: len(x)
        else:
            # integer-based, counting all chat objects
            init_cell = lambda: 0
            update_cell = lambda total, chat: total + 1
            reduce_cell = lambda x: x

        # create 2-dimensional table
        # defaultdict automatically handles proper on-demand initialization of new map entries 
        data = defaultdict(lambda: defaultdict(init_cell))

        # fill inner cells
        for chat in self.matching_chats():
            try:
                # find bucket to change
                var1_value = var1.extract_value(chat, var1_context)
                var2_value = var2.extract_value(chat, var2_context)

                data[var1_value][var2_value] = update_cell(data[var1_value][var2_value], chat)
            except AttributeError:
                pass

        # calc result of cell and row/col/table sums (outer cells)
        for val1, val2 in product(var1_samples, var2_samples):
            # compress cell result
            current = reduce_cell(data[val1][val2])
            data[val1][val2] = current

            # add to: table sum, col sum, row sum
            # setdefault sets value only when it didnt exist already
            data.setdefault(Report.TOTAL_COLUMN, {}).setdefault(Report.TOTAL_COLUMN, 0)
            data[Report.TOTAL_COLUMN][Report.TOTAL_COLUMN] += current

            data.setdefault(val1, {}).setdefault(Report.TOTAL_COLUMN, 0)
            data[val1][Report.TOTAL_COLUMN] += current

            data.setdefault(Report.TOTAL_COLUMN, {}).setdefault(val2, 0)
            data[Report.TOTAL_COLUMN][val2] += current

        return { 'rendered_report': data,
            'variable1_samples': var1_samples + [Report.TOTAL_COLUMN],
            'variable2_samples': var2_samples + [Report.TOTAL_COLUMN],
        }
