from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

class BuddyForm(forms.ModelForm):
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password (again)"), widget=forms.PasswordInput)
    presentForm = forms.BooleanField(label=_("Present registration form to buddy"), required=False)
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "presentForm"]

    def __init__(self, *args, **kwargs):
        super(BuddyForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

