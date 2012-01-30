from django import forms
from django.core.urlresolvers import reverse
from django.forms.util import flatatt
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

class IframeReadonlyWidget(forms.Widget):
    '''displays a FormEntry with labels and answers'''
    
    def __init__(self, attrs=None):
        # The 'rows' and 'cols' attributes are required for HTML correctness.
        default_attrs = {
          'style': 'border: 0px',
          'width': '80%',
        }
        if attrs:
            default_attrs.update(attrs)
        super(IframeReadonlyWidget, self).__init__(default_attrs)

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return mark_safe(u'<iframe src="%s" %s></iframe>' % (
                conditional_escape(force_unicode(reverse("form_entry", args=[value,]))),
                flatatt(final_attrs),
                ))

class IframeEditableWidget(forms.Widget):
    '''displays a FormEntry with labels and answers that can be edited and submitted'''
    
    def __init__(self, attrs=None):
        # The 'rows' and 'cols' attributes are required for HTML correctness.
        default_attrs = {
        'style': 'border: 0px',
        'width': '80%',
        }
        if attrs:
            default_attrs.update(attrs)
        super(IframeEditableWidget, self).__init__(default_attrs)
        
    def render(self, name, value, attrs=None):
        if value is None: return u''
        final_attrs = self.build_attrs(attrs, name=name)
        return mark_safe(u'<iframe src="%s" %s></iframe>' % (
                conditional_escape(force_unicode(reverse("form_entry_edit", args=[value,]))),
                flatatt(final_attrs),
                ))
