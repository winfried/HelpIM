from datetime import datetime

from django import forms
from django.db.models import Max, Min
from django.forms.widgets import Select
from django.forms.extras.widgets import SelectDateWidget
from django.utils.translation import ugettext as _

from helpim.conversations.models import Chat
from helpim.stats.models import Report, ReportVariable


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)

        self.fields['branch'].empty_label = '- %s -' % (_('all branches'))
        self.fields['careworker'].empty_label = '- %s -' % (_('all careworkers'))

        # find choices for Variable fields
        variable_choices = [ tup for var in ReportVariable.all_variables() for tup in var.get_choices_tuples() ]
        self.fields['variable1'].widget = Select(choices=variable_choices)
        self.fields['variable2'].widget = Select(choices=variable_choices)

        # find choices for years-selection of Chats
        try:
            # use year of first/latest Chat
            years = Chat.objects.aggregate(Min('created_at'), Max('created_at'))
            min_year = years['created_at__min'].year
            max_year = years['created_at__max'].year
        except:
            # default to +-5 years from now if no Chats
            min_year = datetime.now().year - 5
            max_year = datetime.now().year + 5
        self.fields['period_start'].widget = SelectDateWidget(years=range(min_year, max_year + 1), required=False)
        self.fields['period_end'].widget = SelectDateWidget(years=range(min_year, max_year + 1), required=False)

    def clean(self):
        '''
        Verify that `period_start` <= `period_end` because > will create an empty result.
        '''

        if 'period_start' in self.cleaned_data and 'period_end' in self.cleaned_data:
            if self.cleaned_data['period_start'] > self.cleaned_data['period_end']:
                raise forms.ValidationError(_('The period of time you selected is invalid (end date is older than start date).'))

        return self.cleaned_data
