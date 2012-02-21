from django.conf import settings
from django.contrib.sites import models as sites_models
from django.contrib.sites.models import Site
from django.dispatch import receiver
from django.db.models.signals import post_syncdb


@receiver(post_syncdb, sender=sites_models)
def create_default_site(sender, verbosity, created_models, **kwargs):
    """
    Create the default site upon 'syncdb' of 'django.contrib.sites'.
    Uses options from settings.py: SITE_ID, SITE_DOMAIN, SITE_NAME.
    """

    if Site in created_models:
        # delete Site objects just created by default by django.contrib.sites
        Site.objects.all().delete()

        # read options from settings.py
        identifier = getattr(settings, 'SITE_ID', 1)
        domain = getattr(settings, 'SITE_DOMAIN', 'example.com')
        name = getattr(settings, 'SITE_NAME', 'example.com')

        # create new default Site
        default_site = Site()
        default_site.domain = domain
        default_site.name = name
        default_site.pk = identifier
        default_site.save()

        if verbosity >= 2:
            print "Creating default Site '%s'" % (default_site.domain)

        Site.objects.clear_cache()
