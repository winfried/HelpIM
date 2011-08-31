# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'BlockedIP'
        db.delete_table('rooms_blockedip')


    def backwards(self, orm):
        
        # Adding model 'BlockedIP'
        db.create_table('rooms_blockedip', (
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('ip_hash', self.gf('django.db.models.fields.CharField')(max_length=32, unique=True)),
        ))
        db.send_create_signal('rooms', ['BlockedIP'])


    models = {
        'conversations.chat': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Chat', '_ormbases': ['conversations.Conversation']},
            'conversation_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['conversations.Conversation']", 'unique': 'True', 'primary_key': 'True'})
        },
        'conversations.conversation': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Conversation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'conversations.participant': {
            'Meta': {'object_name': 'Participant'},
            'blocked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'})
        },
        'rooms.accesstoken': {
            'Meta': {'object_name': 'AccessToken'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Participant']", 'null': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'room': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['rooms.One2OneRoom']", 'null': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'rooms.grouproom': {
            'Meta': {'object_name': 'GroupRoom'},
            'chat': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Chat']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'modified_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'available'", 'max_length': '32'}),
            'status_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'web_clean_exit': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'rooms.one2oneroom': {
            'Meta': {'object_name': 'One2OneRoom'},
            'chat': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Chat']", 'null': 'True'}),
            'client': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['conversations.Participant']"}),
            'client_allocated_at': ('django.db.models.fields.DateTimeField', [], {'default': "'1000-01-01 00:00:00'"}),
            'client_nick': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'modified_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': "orm['conversations.Participant']"}),
            'staff_nick': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'available'", 'max_length': '32'}),
            'status_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'web_clean_exit': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['rooms']
