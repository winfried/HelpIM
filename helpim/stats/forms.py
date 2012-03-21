from datetime import datetime

from django import forms
from django.db.models import Max, Min
from django.forms.extras.widgets import SelectDateWidget
from django.utils.translation import ugettext as _

from helpim.conversations.models import Chat
from helpim.stats.models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report

        try:
            # use year of first/latest Chat
            years = Chat.objects.aggregate(Min('start_time'), Max('start_time'))
            min_year = years['start_time__min'].year
            max_year = years['start_time__max'].year
        except:
            # default to +-5 years from now if no Chats
            min_year = datetime.now().year - 5
            max_year = datetime.now().year + 5

        widgets = {
            'period_start': SelectDateWidget(years=range(min_year, max_year + 1)),
            'period_end': SelectDateWidget(years=range(min_year, max_year + 1)),
        }

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)

        self.fields['branch'].empty_label = '- %s -' % (_('all branches'))
        self.fields['careworker'].empty_label = '- %s -' % (_('all careworkers'))

    def clean(self):
        '''
        Verify that `period_start` <= `period_end` because > will create an empty result.
        '''

        if 'period_start' in self.cleaned_data and 'period_end' in self.cleaned_data:
            if self.cleaned_data['period_start'] > self.cleaned_data['period_end']:
                raise forms.ValidationError(_('The period of time you selected is invalid (end date is older than start date).'))

        return self.cleaned_data
