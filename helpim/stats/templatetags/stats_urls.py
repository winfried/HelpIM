import datetime
import types

from django import template
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
    
    return url