from collections import namedtuple
import os

from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.flatpages.models import FlatPage

NaturalObject = namedtuple('NaturalObject', ['find_by_key', 'make_key'])

class Command(BaseCommand):
    help = 'imports settings of an installation from json'
    args = 'filename [filename ...]'

    natural_objects = {
        'flatpages.FlatPage': NaturalObject(find_by_key=lambda o : FlatPage.objects.get(url=o[0]), make_key=lambda o : (o.url,))
    }

    def handle(self, *files, **options):
        for file in files:
            if not os.path.isfile(file):
                print "Could not find file '%s'" % (file)
                continue

            print 'Loading from %s' % (file)

            # deserialize data, create django model instances
            data = open(file, 'r').read()
            objects = serializers.deserialize('json', data)

            # objects are only instantiated, not yet saved
            for obj in objects:
                # appName.modelName
                key = '%s.%s' % (obj.object._meta.app_label, obj.object._meta.object_name)

                # find natural handler object for this type
                try:
                    natural = Command.natural_objects[key]
                except KeyError:
                    print "don't know how to handle '%s' object, skipping" % (key)
                    continue

                try:
                    # if there is an equal object (as determined by natural key) in the db,
                    # delete it and replace it with the loaded one
                    old_object = natural.find_by_key(natural.make_key(obj.object))
                    old_object.delete()
                except ObjectDoesNotExist:
                    # not finding such an old object is not a problem
                    pass
                finally:
                    # save loaded object, either replacing an old one or being added to the set
                    obj.save()
