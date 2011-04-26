from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from helpim.rooms.bot import Bot

class Command(BaseCommand):
    help = "runs the jabber channel bot"

    option_list = BaseCommand.option_list + (
        make_option('-u', '--username',
                    dest='username',
                    help='Override username from configuration file.'),
        make_option('-n', '--nick',
                    dest='nick',
                    help='Override nick from configuration file.'),
        make_option('-p', '--password',
                    dest='password',
                    help='Override password from configuration file.'),
        make_option('-P', '--port',
                    dest='port',
                    type='int',
                    help='Override port from configuration file.'),
        make_option('-d', '--domain',
                    dest='domain',
                    help='Override domain from configuration file.'),
        make_option('-r', '--resource',
                    dest='resource',
                    help='Override resource from configuration file.'),
        make_option('-m', '--muc-domain',
                    dest='muc_domain',
                    help='Override muc-domain from configuration file.'),
        make_option('-s', '--room-pool-size',
                    dest='room_pool_size',
                    type='int',
                    help='Override room-pool-size from configuration file.'),
        make_option('-l', '--log-level',
                    dest='log_level',
                    type='int',
                    help='Override log-level from configuration file.'),
        make_option('-y', '--log-level-pyxmpp',
                    dest='log_level_pyxmpp',
                    type='int',
                    help='Override log-level-pyxmpp from configuration file.'),
        make_option('-t', '--log-destination',
                    dest='log_destination',
                    help='Override log-destination from configuration file.'),
        )

    def handle(self, *args, **options):
        """ get config """
        conf = BotConfig(settings.BOT)

        """ haters gonna hate """
        for key, val in options.items():
            if val is not None:
                if (key in ['username', 'domain', 'resource', 'password', 'port', 'nick']):
                    setattr(conf.connection, key, val)
                elif (key in ['muc_domain', 'room_pool_size']):
                    if (key == 'muc_domain'):
                        key = 'domain'
                    setattr(conf.muc, key, val)
                else:
                    setattr(conf, key, val)

        """ pass config to bot """
        bot = Bot(conf)

        """ run the bot """
        bot.run()
        pass

class BotConfig:

    def __init__(self, cfg):
        """ we get the config as a dict, but Bot needs the config as
        an object """

        for k, v in cfg.iteritems():
            if type(v).__name__ == 'dict':
                setattr(self, k, BotConfig(v))
            else:
                setattr(self, k, v)

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, k, v):
        return setattr(self, k, v)

