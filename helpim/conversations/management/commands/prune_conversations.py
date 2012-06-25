from datetime import timedelta, datetime
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand

from helpim.conversations.models import Conversation, Message


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            days_to_keep = int(settings.CONVERSATION_KEEP_DAYS)
        except (ValueError, AttributeError):
            raise ImproperlyConfigured("You have not set CONVERSATION_KEEP_DAYS to a number in settings.py")
            sys.exit(1)

        up_for_deletion = datetime.utcnow() - timedelta(days=days_to_keep)

        print >> sys.stderr, "Deleting everything before", up_for_deletion, ".. \nthat is",

        conversations = Conversation.objects.filter(created_at__lt=up_for_deletion)

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
