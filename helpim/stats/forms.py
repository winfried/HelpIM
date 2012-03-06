from django import forms

from helpim.stats.models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
