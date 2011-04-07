from django.core.management.base import BaseCommand, CommandError
from helpim.bot import Bot

class Command(BaseCommand):
    help = "runs the jabber channel bot"

    def handle(self, *args, **options):
        """ get config """
        
        """ pass config to bot """
        bot = Bot()

        """ run the bot """
        bot.run()
        pass
