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
