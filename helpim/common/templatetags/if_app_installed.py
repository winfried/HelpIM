from django import template
from django.conf import settings
from django.utils.encoding import smart_str

register = template.Library()

@register.tag('ifappinstalled')
def do_if_app_installed(parser, token):
    """
    The ``{% ifappinstalled %}`` tag takes one app name and only if that app is installed, the contents of the block are output.
    This tag does not support {% else %} or multiple app names.
    Example: ``{% ifappinstalled helpim.buddychat %} Buddychat is installed {% endifappinstalled %}``
    Note that you must not put the app name in quotation marks.
    """

    try:
        tag_name, appname = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires 1 argument" % token.contents.split()[0])

    nodelist = parser.parse(('endifappinstalled',))
    parser.delete_first_token()

    return IfAppInstalledNode(appname, nodelist)

class IfAppInstalledNode(template.Node):
    def __init__(self, appname, nodelist):
        self.appname = appname
        self.nodelist = nodelist

    def render(self, context):
        if self.appname in settings.INSTALLED_APPS:
            return self.nodelist.render(context)
        else:
            return ''
