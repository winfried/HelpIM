# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Deleting field 'Chat.room'
        db.delete_column('conversations_chat', 'room')


    def backwards(self, orm):

        # Adding field 'Chat.room'
        db.add_column('conversations_chat', 'room', self.gf('django.db.models.fields.IntegerField')(default=-1), keep_default=False)


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
            'conversation_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['conversations.Conversation']", 'unique': 'True', 'primary_key': 'True'})
        },
        'conversations.chatmessage': {
            'Meta': {'object_name': 'ChatMessage', '_ormbases': ['conversations.Message']},
            'event': ('django.db.models.fields.CharField', [], {'default': "'message'", 'max_length': '10'}),
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
            'comments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['threadedcomments.ThreadedComment']", 'symmetrical': 'False'}),
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Participant']"}),
            'sender_name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'conversations.participant': {
            'Meta': {'object_name': 'Participant'},
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'})
        },
        'threadedcomments.threadedcomment': {
            'Meta': {'ordering': "('-date_submitted',)", 'object_name': 'ThreadedComment'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'date_approved': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_submitted': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'markup': ('django.db.models.fields.IntegerField', [], {'default': '5', 'null': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children'", 'null': 'True', 'blank': 'True', 'to': "orm['threadedcomments.ThreadedComment']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['conversations']
