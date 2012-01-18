import datetime
import types

from django import template
from django.core.urlresolvers import reverse
from django.template.defaultfilters import stringfilter


register = template.Library()

@register.filter
@stringfilter
def stats_details(value, arg):
    """
    Combines the URL or format string returned by StatsProvider.get_detail_url() and the format values given by arg depending on its type.
    """
    url = u''
    
    if isinstance(arg, types.NoneType):
        return url
    elif isinstance(arg, datetime.date):
        url = value % {'year':arg.year, 'month':arg.month, 'day':arg.day}
    elif isinstance(arg, types.LongType):
        url = reverse(value, args=[arg])
    
    return url

@register.filter
def key(value, arg):
    '''
    Retrieves value given by key 'arg' from dictionary 'value'.
    This way, a dictionary can be accessed using a template variable as key.
    See: https://code.djangoproject.com/ticket/3371
    '''

    return value.get(arg, '')
