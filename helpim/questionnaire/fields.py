import re

from django import forms
from django.forms.widgets import RadioFieldRenderer
from django.utils.html import escapejs
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe

import forms_builder.forms.fields
from helpim.utils import OrderedDict

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

    def render(self, name, value, attrs={}, choices=None):

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

        attrs["class"]="scalefield"

        choices = [(i, '') for i in xrange(1, scaling + 1)]

        rendered = RadioFieldRenderer(
                      name, value, attrs, choices
                    ).render()

        rendered = re.sub("<\/?ul>", "", rendered)
        rendered = re.sub("<\/?li>", "", rendered)

        return mark_safe(
            "<p>" +
            '<label class="scaleupper">' + upper_label + "</label>" +
            rendered +
            '<label class="scalelower">' + lower_label + "</label></p>"
        )


class DoubleDropField(forms.MultiValueField):
    """
    >>> from helpim.questionnaire.fields import DoubleDropField
    >>> ddf = DoubleDropField()
    >>> ddf._parseChoices('one(),two(A,B,C),three')
    OrderedDict([('one', ['---']), ('two', ['A', 'B', 'C']), ('three', ['---'])])
    >>> ddf._parseChoices('one, two,      three')
    OrderedDict([('one', ['---']), ('two', ['---']), ('three', ['---'])])
    >>> ddf._parseChoices('one(1,2),two,three()')
    OrderedDict([('one', ['1', '2']), ('two', ['---']), ('three', ['---'])])
    >>> ddf._parseChoices('one(1,2),two(X,Y),three(C)')
    OrderedDict([('one', ['1', '2']), ('two', ['X', 'Y']), ('three', ['C'])])
    """

    def __init__(self, choices={}, *args, **kwargs):
        choicesText = ",".join([c[0] for c in choices])
        self.choicesDict = self._parseChoices(choicesText)
        mainChoices = [(c, c) for c in self.choicesDict.keys()]

        fields = [forms.ChoiceField(choices=mainChoices), forms.ChoiceField()]
        super(DoubleDropField, self).__init__(fields, *args, **kwargs)

        self.widget.choicesDict = self.choicesDict

    def compress(self, data_list):
        if data_list:
            return "%s>>>%s" % (data_list[0], data_list[1])
        else:
            return None

    def clean(self, value):
        # set choices for second combobox according to what is selected in first combobox
        if len(value) == 2 and self.choicesDict.has_key(value[0]):
            self.fields[1].choices = [(c, c) for c in self.choicesDict[value[0]]]

        return super(DoubleDropField, self).clean(value)

    def _parseChoices(self, inputText):
        result = OrderedDict()
        read = ""
        mainCat = ''
        subList = False

        for char in inputText:
            if char == '(' and not subList:
                subList = True

                read = read.strip()
                if read:
                    result[read] = []
                    mainCat = read
                    read = ""
            elif char == ')' and subList:
                subList = False

                read = read.strip()
                if read:
                    result[mainCat] += [read]
                    mainCat = ''
                    read = ''
                else:
                    result[mainCat] += ['---']
            elif char == ',':
                read = read.strip()
                if read:
                    if subList:
                        result[mainCat] += [read]
                        read = ""
                    else:
                        result[read] = ['---']
                        mainCat = read
                        read = ""
            else:
                read += char

        # add last item
        read = read.strip()
        if read:
            if subList:
                result[mainCat] += [read]
            else:
                result[read] = ['---']

        return result

class DoubleDropWidget(forms.MultiWidget):
    """
    >>> from helpim.questionnaire.fields import DoubleDropWidget
    >>> from helpim.questionnaire.fields import DoubleDropField
    >>> ddw = DoubleDropWidget()
    >>> ddf = DoubleDropField()
    >>> ddw.choicesDict = ddf._parseChoices('one(),two(A,B,C),three(X)')
    >>> result = ddw._renderJavascript('mainId', 'subId')
    >>> 'subList.push(["A", "B", "C"]);' in result
    True
    >>> 'subList.push(["X"]);' in result
    True
    
    >>> ddw.choicesDict = ddf._parseChoices('one("quotedstring")')
    >>> result = ddw._renderJavascript('mainId', 'subId')
    >>> 'subList.push(["\\u0022quotedstring\\u0022"]);' in result
    True
    """
    
    def __init__(self, attrs=None):
        widgets = [forms.Select(), forms.Select()]
        super(DoubleDropWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split(">>>")
        else:
            return [None, None]

    def render(self, name, value, attrs=None):
        # set choices for combo boxes
        mainChoices = [(c, c) for c in self.choicesDict.keys()]
        self.widgets[0].choices = mainChoices

        try:
            if value:
                # fill second combo box with subChoices of current mainChoice
                mainValue = value[0]
                self.widgets[1].choices = [(c, c) for c in self.choicesDict[mainValue]]
            else:
                # fill second combo box with subChoices of first mainChoice
                self.widgets[1].choices = [(c, c) for c in self.choicesDict.iteritems().next()[1]]
        except:
            pass

        # super class takes care of assigning "selected" attribute to <option/>
        renderedSelects = super(DoubleDropWidget, self).render(name, value, attrs)
        renderedJavascript = self._renderJavascript(attrs['id'] + '_0', attrs['id'] + '_1')

        return renderedSelects + renderedJavascript

    def _renderJavascript(self, mainListId, subListId):
        output = []

        output.append(u'<script type="text/javascript">')
        output.append(u'var subList = new Array();')

        for k, v in self.choicesDict.iteritems():
            if len(v) > 0:
                output.append(u'subList.push([%s]);' % (', '.join(['"%s"' % (escapejs(el)) for el in v])))
            else:
                output.append(u'subList.push(["---"]);')

        output.append(u'new helpim.DoubleDrop("%s", "%s", subList).start();' % (mainListId, subListId))
        output.append(u'</script>')

        return mark_safe(u'\n'.join(output))
