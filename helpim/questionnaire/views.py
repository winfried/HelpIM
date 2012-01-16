
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

from helpim.questionnaire.fields import DoubleDropWidget


def form_detail(request, slug, template="questionnaire/form_detail.html"):
    """
    Display a built form and handle submission.
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
        if not form_for_form.is_valid():
            form_invalid.send(sender=request, form=form_for_form)
        else:
            entry = form_for_form.save()
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
            form_valid.send(sender=request, form=form_for_form, entry=entry)
            return redirect(reverse("form_sent", kwargs={"slug": form.slug, "entry": entry.pk}))
    context = {"form": form, "form_for_form": form_for_form}
    return render_to_response(template, context, RequestContext(request))


def form_sent(request, slug, entry=None, template="forms/form_sent.html"):
    """
    Show the response message.
    """
    published = Form.objects.published(for_user=request.user)
    form = get_object_or_404(published, slug=slug)
    entry = FormEntry.objects.get(pk=entry)
    context = {"form": form, "entry": entry}
    return render_to_response(template, context, RequestContext(request))

def form_entry(request, form_entry_id, template="forms/form_entry.html"):

    form_entry = get_object_or_404(FormEntry, id=form_entry_id)

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
