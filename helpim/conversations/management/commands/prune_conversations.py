import sys

from datetime import timedelta, datetime
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

        up_for_deletion = datetime.utcnow() - timedelta(days=days_to_keep)

        print >> sys.stderr, "Deleting everything before", up_for_deletion

        query = Conversation.objects.filter(start_time__lt=up_for_deletion)

        print >> sys.stderr, "Deleting %d conversations .." % query.count(),

        query.delete()

        print >> sys.stderr, "done."

