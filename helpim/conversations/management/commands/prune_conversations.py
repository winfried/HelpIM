from datetime import timedelta, datetime
import sys

from django.core.management.base import BaseCommand

from helpim.conversations.models import Conversation, Message


class Command(BaseCommand):
    def handle(self, days_to_keep, **options):
        try:
            days_to_keep = int(days_to_keep)
        except ValueError:
            print >> sys.stderr, "days_to_keep: must be a number"
            print >> sys.stderr, "Usage: ./manage.py prune_conversations [days_to_keep]"
            sys.exit(1)

        up_for_deletion = datetime.utcnow() - timedelta(days=days_to_keep)

        print >> sys.stderr, "Deleting everything before", up_for_deletion, ".. \nthat is",

        conversations = Conversation.objects.filter(start_time__lt=up_for_deletion)

        messages = Message.objects.filter(conversation__in=conversations)

        print >> sys.stderr, (
              "%d conversations, that is %d messages .." % (
                conversations.count(),
                messages.count(),
              )),

        # empty contents of messages
        for msg in messages:
            msg.body = '*****'
            msg.save()

        print >> sys.stderr, "done."

