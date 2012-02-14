# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'BuddyChatProfile.volunteer'
        db.delete_column('buddychat_buddychatprofile', 'volunteer_id')

        # Adding field 'BuddyChatProfile.careworker'
        db.add_column('buddychat_buddychatprofile', 'careworker', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True), keep_default=False)

        # Adding field 'BuddyChatProfile.careworker_conversation'
        db.add_column('buddychat_buddychatprofile', 'careworker_conversation', self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='+', to=orm['conversations.Conversation']), keep_default=False)

        # Adding field 'BuddyChatProfile.coordinator_conversation'
        db.add_column('buddychat_buddychatprofile', 'coordinator_conversation', self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='+', to=orm['conversations.Conversation']), keep_default=False)

        # Adding field 'BuddyChatProfile.careworker_coordinator_conversation'
        db.add_column('buddychat_buddychatprofile', 'careworker_coordinator_conversation', self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='+', to=orm['conversations.Conversation']), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'BuddyChatProfile.volunteer'
        db.add_column('buddychat_buddychatprofile', 'volunteer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True), keep_default=False)

        # Deleting field 'BuddyChatProfile.careworker'
        db.delete_column('buddychat_buddychatprofile', 'careworker_id')

        # Deleting field 'BuddyChatProfile.careworker_conversation'
        db.delete_column('buddychat_buddychatprofile', 'careworker_conversation_id')

        # Deleting field 'BuddyChatProfile.coordinator_conversation'
        db.delete_column('buddychat_buddychatprofile', 'coordinator_conversation_id')

        # Deleting field 'BuddyChatProfile.careworker_coordinator_conversation'
        db.delete_column('buddychat_buddychatprofile', 'careworker_coordinator_conversation_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'buddychat.buddychatprofile': {
            'Meta': {'object_name': 'BuddyChatProfile', '_ormbases': ['registration.RegistrationProfile']},
            'careworker': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'careworker_conversation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['conversations.Conversation']"}),
            'careworker_coordinator_conversation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['conversations.Conversation']"}),
            'coordinator_conversation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['conversations.Conversation']"}),
            'coupled_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'ready': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'registrationprofile_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['registration.RegistrationProfile']", 'unique': 'True', 'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'conversations.conversation': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Conversation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'registration.registrationprofile': {
            'Meta': {'object_name': 'RegistrationProfile'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['buddychat']
