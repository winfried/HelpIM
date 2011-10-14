# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Questionnaire'
        db.create_table('questionnaire_questionnaire', (
            ('form_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['forms.Form'], unique=True, primary_key=True)),
            ('position', self.gf('django.db.models.fields.CharField')(unique=True, max_length=3)),
        ))
        db.send_create_signal('questionnaire', ['Questionnaire'])

        # Adding model 'ConversationFormEntry'
        db.create_table('questionnaire_conversationformentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entry', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['forms.FormEntry'])),
            ('conversation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Conversation'])),
            ('position', self.gf('django.db.models.fields.CharField')(max_length=3)),
        ))
        db.send_create_signal('questionnaire', ['ConversationFormEntry'])

        # Adding unique constraint on 'ConversationFormEntry', fields ['conversation', 'position']
        db.create_unique('questionnaire_conversationformentry', ['conversation_id', 'position'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'ConversationFormEntry', fields ['conversation', 'position']
        db.delete_unique('questionnaire_conversationformentry', ['conversation_id', 'position'])

        # Deleting model 'Questionnaire'
        db.delete_table('questionnaire_questionnaire')

        # Deleting model 'ConversationFormEntry'
        db.delete_table('questionnaire_conversationformentry')


    models = {
        'conversations.conversation': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Conversation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'forms.form': {
            'Meta': {'object_name': 'Form'},
            'button_text': ('django.db.models.fields.CharField', [], {'default': "u'Submit'", 'max_length': '50'}),
            'email_copies': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'email_from': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'email_message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email_subject': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'expiry_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'send_email': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'forms.formentry': {
            'Meta': {'object_name': 'FormEntry'},
            'entry_time': ('django.db.models.fields.DateTimeField', [], {}),
            'form': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['forms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'questionnaire.conversationformentry': {
            'Meta': {'unique_together': "(('conversation', 'position'),)", 'object_name': 'ConversationFormEntry'},
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']"}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['forms.FormEntry']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire', '_ormbases': ['forms.Form']},
            'form_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['forms.Form']", 'unique': 'True', 'primary_key': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'})
        }
    }

    complete_apps = ['questionnaire']
