# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'One2OneRoom'
        db.create_table('rooms_one2oneroom', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('jid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('status', self.gf('django.db.models.fields.CharField')(default='available', max_length=32)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('chat', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Chat'], null=True)),
            ('web_clean_exit', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('modified_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('staff', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['conversations.Participant'])),
            ('staff_nick', self.gf('django.db.models.fields.CharField')(max_length=64, null=True)),
            ('client', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['conversations.Participant'])),
            ('client_nick', self.gf('django.db.models.fields.CharField')(max_length=64, null=True)),
        ))
        db.send_create_signal('rooms', ['One2OneRoom'])

        # Adding model 'GroupRoom'
        db.create_table('rooms_grouproom', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('jid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('status', self.gf('django.db.models.fields.CharField')(default='available', max_length=32)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('chat', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Chat'], null=True)),
            ('web_clean_exit', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('modified_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('rooms', ['GroupRoom'])


    def backwards(self, orm):

        # Deleting model 'One2OneRoom'
        db.delete_table('rooms_one2oneroom')

        # Deleting model 'GroupRoom'
        db.delete_table('rooms_grouproom')


    models = {
        'conversations.chat': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Chat', '_ormbases': ['conversations.Conversation']},
            'conversation_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['conversations.Conversation']", 'unique': 'True', 'primary_key': 'True'}),
            'room': ('django.db.models.fields.IntegerField', [], {})
        },
        'conversations.conversation': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Conversation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'conversations.participant': {
            'Meta': {'object_name': 'Participant'},
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'})
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
