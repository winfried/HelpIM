import sys

from datetime import timedelta
from django.db.models import F

from django.core.management.base import BaseCommand, CommandError
from helpim.conversations.models import Conversation

class Command(BaseCommand):
    def handle(self, days_to_keep, **options):
        try:
            days_to_keep = int(days_to_keep)
        except ValueError:
            print >> sys.stderr, "days_to_keep: must be a number"
            print >> sys.stderr, "Usage: ./manage.py prune_conversations [days_to_keep]"
            sys.exit(1)

        query = Conversation.objects.filter(
                start_time__gt=F('start_time') + timedelta(days=days_to_keep))

        print "Deleting %d conversations .." % query.count(),

        query.delete()

        print "done."

