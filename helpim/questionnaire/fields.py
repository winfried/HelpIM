import re

from django import forms
from django.forms.widgets import RadioFieldRenderer
from django.utils.translation import ugettext as _

import forms_builder.forms.fields

def register_forms_builder_field_type(identifier, name, field_class, widget_class=None):

    if identifier in forms_builder.forms.fields.CHOICES:
        return # already added

    forms_builder.forms.fields.CHOICES += (identifier,)
    forms_builder.forms.fields.NAMES += ((identifier, name),)
    forms_builder.forms.fields.CLASSES[identifier] = field_class

    if widget_class:
        forms_builder.forms.fields.WIDGETS.update({
          identifier: widget_class,
        })

    # this is some bad hack to get the new field types recognized by forms_builder
    # http://stackoverflow.com/questions/2388798/set-model-field-choices-attribute-at-run-time
    forms_builder.forms.models.Field._meta.get_field_by_name('field_type')[0]._choices = forms_builder.forms.fields.NAMES

class ScaleField(forms.ChoiceField):
    def valid_value(self, value):
        try:
          scaling = int(self.choices[0][1])
        except ValueError:
          scaling = 5

        try:
            return int(value, 10) in xrange(1, scaling + 1)
        except ValueError:
            return False

class ScaleWidget(forms.RadioSelect):

    """
    Choices given to this widget take the following form:

    (5, 'I very much agree with this', 'I very much disagree')

    Where 5 is the number of steps the user can weight his answer, the first
    string is the upper label and the second string is the lower level.

    """

    def render(self, name, value, attrs=None, choices=None):

        try:
          scaling = int(self.choices[0][1], 10)
        except ValueError:
          scaling = 5

        try:
          upper_label = self.choices[1][1]
        except ValueError:
          upper_label = _("Agree")

        try:
          lower_label = self.choices[2][1]
        except ValueError:
          lower_label = _("Disagree")

        choices = [(i, '') for i in xrange(1, scaling + 1)]

        return ("<div class='helpim-questionnaire-scale'><ul><li>" +
                upper_label +
                "</li>" +
                re.sub(
                    "<\/?ul>",
                    "",
                    RadioFieldRenderer(
                      name, value, attrs, choices
                    ).render()
                ) +
                "<li>" +
                lower_label +
                "</li></ul></div>")
