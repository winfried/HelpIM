from collections import namedtuple
import os

from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.flatpages.models import FlatPage

from helpim.questionnaire.models import Questionnaire
from forms_builder.forms.models import Field, Form

NaturalObject = namedtuple('NaturalObject', ['find_by_key', 'make_key'])

class Command(BaseCommand):
    help = 'imports settings of an installation from json'
    args = 'filename [filename ...]'

    def handle(self, *files, **options):
        # build dictionary of objects we know how to import
        self.natural_objects = {
            'flatpages.FlatPage': NaturalObject(find_by_key=lambda o: FlatPage.objects.get(url=o[0]), make_key=lambda o: (o.url,)),
            'auth.Group': NaturalObject(find_by_key=lambda o: Group.objects.get(name=o[0]), make_key=lambda o: (o.name,)),
        }

        # only import questionnaire objects when db is safe
        if Questionnaire.objects.all().count() == 0 and Form.objects.all().count() == 0 and Field.objects.all().count() == 0:
            self.natural_objects.update({
                'questionnaire.Questionnaire': NaturalObject(find_by_key=None, make_key=None),
                'forms.Form': NaturalObject(find_by_key=None, make_key=None),
                'forms.Field': NaturalObject(find_by_key=None, make_key=None),
            })

        for file in files:
            if not os.path.isfile(file):
                self.stdout.write("Could not find file '%s'" % (file))
                continue

            self.stdout.write('Loading from %s' % (file))

            # deserialize data, create django model instances
            data = open(file, 'r').read()
            objects = serializers.deserialize('json', data)

            # objects are only instantiated, not yet saved
            for obj in objects:
                # appName.modelName
                key = '%s.%s' % (obj.object._meta.app_label, obj.object._meta.object_name)

                # find natural handler object for this type
                try:
                    natural = self.natural_objects[key]
                except KeyError:
                    self.stdout.write("don't know how to handle '%s' object, skipping" % (key))
                    continue

                if natural.find_by_key is None:
                    # plain-old, dumb importing, susceptible to PK-collisions
                    obj.save()
                else:
                    try:
                        # if there is an equal object (as determined by natural key) in the db,
                        # delete it and replace it with the loaded one
                        old_object = natural.find_by_key(natural.make_key(obj.object))
                        if old_object:
                            old_object.delete()
                    except ObjectDoesNotExist:
                        # not finding such an old object is not a problem
                        pass
                    finally:
                        # sql-insert loaded object, either replacing an old one or being added to the set
                        # then attach m2m-models to it
                        obj.object.pk = None
                        obj.object.id = None
                        obj.object.save(force_insert=True)
                        for accessor_name, object_list in obj.m2m_data.items():
                            setattr(obj.object, accessor_name, object_list)
                        obj.save()
