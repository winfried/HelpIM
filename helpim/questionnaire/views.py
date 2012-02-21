
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.http import urlquote

from forms_builder.forms.fields import WIDGETS
from forms_builder.forms.forms import FormForForm
from forms_builder.forms.models import Form, FormEntry, Field
from forms_builder.forms.settings import USE_SITES
from forms_builder.forms.signals import form_invalid, form_valid

from helpim.conversations.models import Conversation
from helpim.questionnaire.fields import DoubleDropWidget
from helpim.questionnaire.models import questionnaire_saved

# ony load buddychat models when buddychat app is installed
# its needed here to redirect to a BuddyChatProfile after questionnaire submission
if 'helpim.buddychat' in settings.INSTALLED_APPS:
    from helpim.buddychat.models import BuddyChatProfile

def form_detail(request, slug, template="questionnaire/form_detail.html", extra_object_id=None):
    """
    Display a built form and handle its submission.
    
    object_id is the primary key of an object like Conversation or BuddyChatProfile that will be linked to this FormEntry
    via ConversationFormEntry or QuestionnaireFormEntry.
    """

    published = Form.objects.published(for_user=request.user)
    if USE_SITES:
        published = published.filter(sites=Site.objects.get_current())
    form = get_object_or_404(published, slug=slug)

    if form.login_required and not request.user.is_authenticated():
        return redirect("%s?%s=%s" % (settings.LOGIN_URL, REDIRECT_FIELD_NAME,
                        urlquote(request.get_full_path())))

    args = (form, request.POST or None, request.FILES or None)
    form_for_form = FormForForm(*args)

    if request.method == "POST":
        has_extra_permission = False

        # if the id of an extra object is given, make sure user has permissions and preconditions are met
        if extra_object_id > 0:
            if form.questionnaire.position == 'SC':
                conv = get_object_or_404(Conversation, pk=extra_object_id)

                # only staff member assigned to Conversation may take SC-Questionnaire
                has_permission = (conv.getStaff().user == request.user)
                # the SC-Questionnaire can be taken only once
                doesnt_exist = (form.questionnaire.conversationformentry_set.filter(conversation__id=extra_object_id).count() == 0)

                has_extra_permission = has_permission and doesnt_exist
            elif form.questionnaire.position == 'CR':
                profile = get_object_or_404(BuddyChatProfile, pk=extra_object_id)

                has_permission = (profile.user == request.user)
                doesnt_exist = (profile.questionnaires.filter(position='CR').count() == 0)

                has_extra_permission = has_permission and doesnt_exist
            elif form.questionnaire.position == 'CX':
                profile = get_object_or_404(BuddyChatProfile, pk=extra_object_id)
                has_extra_permission = (profile.user == request.user)
            elif form.questionnaire.position == 'SX':
                profile = get_object_or_404(BuddyChatProfile, pk=extra_object_id)

                # only careworker assigned to BuddyProfile may take SX-Questionnaire
                has_extra_permission = (profile.careworker == request.user)


        if not form_for_form.is_valid() or (extra_object_id > 0 and not has_extra_permission):
            form_invalid.send(sender=request, form=form_for_form)
        else:
            entry = form_for_form.save()

            # send email
            fields = ["%s: %s" % (v.label, form_for_form.cleaned_data[k])
                for (k, v) in form_for_form.fields.items()]
            subject = form.email_subject
            if not subject:
                subject = "%s - %s" % (form.title, entry.entry_time)
            body = "\n".join(fields)
            if form.email_message:
                body = "%s\n\n%s" % (form.email_message, body)
            email_from = form.email_from or settings.DEFAULT_FROM_EMAIL
            email_to = form_for_form.email_to()
            if email_to and form.send_email:
                msg = EmailMessage(subject, body, email_from, [email_to])
                msg.send()
            email_from = email_to or email_from # Send from the email entered.
            email_copies = [e.strip() for e in form.email_copies.split(",")
                if e.strip()]
            if email_copies:
                msg = EmailMessage(subject, body, email_from, email_copies)
                for f in form_for_form.files.values():
                    f.seek(0)
                    msg.attach(f.name, f.read())
                msg.send()

            # send signals
            form_valid.send(sender=request, form=form_for_form, entry=entry)
            questionnaire_saved.send(sender=request, questionnaire=form.questionnaire, entry=entry, extra_object_id=extra_object_id)

            return redirect(reverse("form_sent", kwargs={"slug": form.slug, "entry": entry.pk}))

    context = {
        "form": form,
        "form_for_form": form_for_form,
    }

    return render_to_response(template, context, RequestContext(request))


def form_sent(request, slug, entry=None, template="forms/form_sent.html"):
    """
    Show the response message.
    """
    published = Form.objects.published(for_user=request.user)
    form = get_object_or_404(published, slug=slug)

    # if Form requires login, dont show to Anonymous
    if form.login_required and not request.user.is_authenticated():
        return redirect("%s?%s=%s" % (settings.LOGIN_URL, REDIRECT_FIELD_NAME,
                        urlquote(request.get_full_path())))

    entry = FormEntry.objects.get(pk=entry)
    context = {"form": form, "entry": entry}
    return render_to_response(template, context, RequestContext(request))

def form_entry(request, form_entry_id, template="forms/form_entry.html"):
    '''Show answers of FormEntry'''

    form_entry = get_object_or_404(FormEntry, id=form_entry_id)

    is_same_user = False
    try:
        is_same_user = (form_entry.questionnaireformentry_set.all()[0].buddychat_profile.user == request.user)
    except:
        is_same_user = False

    # must be staff member, or in case of BuddyChat same user who created the FormEntry
    if not request.user.is_staff and (not is_same_user):
        return redirect("%s?%s=%s" % (settings.LOGIN_URL, REDIRECT_FIELD_NAME, urlquote(request.get_full_path())))

    form_entries = form_entry.fields.all()
    fields = Field.objects.filter(pk__in=[form_entry.field_id for form_entry in form_entries])

    return render_to_response(template, {
      "fields_and_entries": zip(fields, form_entries),
    }, RequestContext(request))

def form_entry_edit(request, form_entry_id, template='forms/form_entry_edit.html'):
    form_entry = get_object_or_404(FormEntry, id=form_entry_id)
    form_entry_fields = form_entry.fields.all()
    the_form = form_entry.form
    conversation_form_entry = form_entry.conversationformentry_set.all()[0]

    # enforce permissions, must have special right or be staff in current conversation to continue
    if not request.user.has_perm('questionnaire.can_revise_questionnaire') and not request.user == conversation_form_entry.conversation.getStaff().user:
        return redirect('/admin')


    if request.method == 'POST':
        args = (the_form, request.POST or None, request.FILES or None)
        form_for_form = FormForForm(*args)
        if form_for_form.is_valid():

            # save new FormEntry, assign to ConversationFormEntry
            entry = form_for_form.save()
            conversation_form_entry.entry = entry
            conversation_form_entry.save()

            # delete old FormEntry and FieldEntry
            form_entry.fields.all().delete()
            form_entry.conversationformentry_set.clear()
            form_entry.delete()

            # redirect to conversation-detail-page, store conversation id before so it remains known
            return redirect('form_entry_edit', form_entry_id=entry.id)

    # convert FormEntry to dictionary to initialize FormForForm (django-forms-builder doesnt support editing instances)
    data = QueryDict('', mutable=True)
    the_fields = []
    for entry_field in form_entry_fields:
        the_field = Field.objects.get(pk=entry_field.field_id)
        the_fields.append(the_field)
        
        widget = WIDGETS.get(the_field.field_type)
        
        if widget == DoubleDropWidget:
            for i, val in enumerate(DoubleDropWidget().decompress(entry_field.value)):
                data['field_%s_%s' % (entry_field.field_id, i)] = val
        else:
            data['field_%s' % entry_field.field_id] = entry_field.value

    args = (the_form, data, request.FILES or None)
    form_for_form = FormForForm(*args)

    return render_to_response(template, {
        'form': the_form,
        "form_for_form": form_for_form,
    }, RequestContext(request))
