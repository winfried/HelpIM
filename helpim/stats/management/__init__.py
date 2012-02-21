from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_syncdb
from django.dispatch import receiver

from helpim.stats import models as stats_models


@receiver(post_syncdb, sender=stats_models)
def create_stats_permissions(sender, verbosity, **kwargs):
    """
    Create global permissions required by app 'helpim.stats'.
    Since the stats app doesn't have any model classes, we use: http://tomcoote.co.uk/django/global-django-permissions/
    """
    # create new ContentType to base permissions on
    content_type, created = ContentType.objects.get_or_create(model='', app_label='stats',
                                                              defaults={'name': 'stats'})

    # create permissions
    p, created = Permission.objects.get_or_create(codename='can_view_stats', content_type=content_type,
                                                  defaults={'name': 'Can view Stats', 'content_type': content_type})

    if created and verbosity >= 2:
        print "Adding permission 'can_view_stats'"
