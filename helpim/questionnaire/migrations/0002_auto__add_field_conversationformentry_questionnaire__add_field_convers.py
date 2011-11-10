# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ConversationFormEntry.questionnaire'
        db.add_column('questionnaire_conversationformentry', 'questionnaire', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['questionnaire.Questionnaire']), keep_default=False)

        # Adding field 'ConversationFormEntry.created_at'
        db.add_column('questionnaire_conversationformentry', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.datetime(2011, 11, 10, 13, 28, 31, 132679), blank=True), keep_default=False)

        # Adding field 'ConversationFormEntry.entry_at'
        db.add_column('questionnaire_conversationformentry', 'entry_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)

        # Changing field 'ConversationFormEntry.conversation'
        db.alter_column('questionnaire_conversationformentry', 'conversation_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conversations.Conversation'], null=True))

        # Changing field 'ConversationFormEntry.entry'
        db.alter_column('questionnaire_conversationformentry', 'entry_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['forms.FormEntry'], null=True))


    def backwards(self, orm):
        
        # Deleting field 'ConversationFormEntry.questionnaire'
        db.delete_column('questionnaire_conversationformentry', 'questionnaire_id')

        # Deleting field 'ConversationFormEntry.created_at'
        db.delete_column('questionnaire_conversationformentry', 'created_at')

        # Deleting field 'ConversationFormEntry.entry_at'
        db.delete_column('questionnaire_conversationformentry', 'entry_at')

        # User chose to not deal with backwards NULL issues for 'ConversationFormEntry.conversation'
        raise RuntimeError("Cannot reverse this migration. 'ConversationFormEntry.conversation' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'ConversationFormEntry.entry'
        raise RuntimeError("Cannot reverse this migration. 'ConversationFormEntry.entry' and its values cannot be restored.")


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
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conversations.Conversation']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['forms.FormEntry']", 'null': 'True', 'blank': 'True'}),
            'entry_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['questionnaire.Questionnaire']"})
        },
        'questionnaire.questionnaire': {
            'Meta': {'object_name': 'Questionnaire', '_ormbases': ['forms.Form']},
            'form_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['forms.Form']", 'unique': 'True', 'primary_key': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'})
        }
    }

    complete_apps = ['questionnaire']
