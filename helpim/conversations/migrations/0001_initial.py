# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Conversation'
        db.create_table('conversations_conversation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
        ))
        db.send_create_signal('conversations', ['Conversation'])

        # Adding model 'Participant'
        db.create_table('conversations_participant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conversation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Conversation'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('conversations', ['Participant'])

        # Adding model 'Message'
        db.create_table('conversations_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conversation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Conversation'])),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Participant'])),
            ('sender_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('conversations', ['Message'])

        # Adding model 'MessageComment'
        db.create_table('conversations_messagecomment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.MessageComment'])),
            ('message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Message'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('conversations', ['MessageComment'])

        # Adding model 'Chat'
        db.create_table('conversations_chat', (
            ('conversation_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['conversations.Conversation'], unique=True, primary_key=True)),
            ('room', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('conversations', ['Chat'])

        # Adding model 'ChatMessage'
        db.create_table('conversations_chatmessage', (
            ('message_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['conversations.Message'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('conversations', ['ChatMessage'])


    def backwards(self, orm):

        # Deleting model 'Conversation'
        db.delete_table('conversations_conversation')

        # Deleting model 'Participant'
        db.delete_table('conversations_participant')

        # Deleting model 'Message'
        db.delete_table('conversations_message')

        # Deleting model 'MessageComment'
        db.delete_table('conversations_messagecomment')

        # Deleting model 'Chat'
        db.delete_table('conversations_chat')

        # Deleting model 'ChatMessage'
        db.delete_table('conversations_chatmessage')


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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'conversations.chat': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Chat', '_ormbases': ['conversations.Conversation']},
            'conversation_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['conversations.Conversation']", 'unique': 'True', 'primary_key': 'True'}),
            'room': ('django.db.models.fields.IntegerField', [], {})
        },
        'conversations.chatmessage': {
            'Meta': {'object_name': 'ChatMessage', '_ormbases': ['conversations.Message']},
            'message_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['conversations.Message']", 'unique': 'True', 'primary_key': 'True'})
        },
        'conversations.conversation': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Conversation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'conversations.message': {
            'Meta': {'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Participant']"}),
            'sender_name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'conversations.messagecomment': {
            'Meta': {'object_name': 'MessageComment'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'body': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Message']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.MessageComment']"})
        },
        'conversations.participant': {
            'Meta': {'object_name': 'Participant'},
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['conversations']
