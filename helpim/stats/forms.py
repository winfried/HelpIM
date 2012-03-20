from django import forms
from django.forms.extras.widgets import SelectDateWidget
from django.utils.translation import ugettext as _

from helpim.stats.models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        widgets = {
            # TODO: use `years`:List available years in selection
            'period_start': SelectDateWidget(),
            'period_end': SelectDateWidget(),
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
