from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from serebii.utils import bbcode_to_html

register = template.Library()

@register.filter
def parse_bbcode(text):
    return mark_safe(bbcode_to_html(text))

@register.simple_tag
def optional_year_url(route_name, *args, **kwargs):
    if 'year' in kwargs and kwargs['year'] in (None, settings.YEAR):
        # We don't need the year in the URL
        kwargs.pop('year')
    return reverse(route_name, kwargs=kwargs)

@register.simple_tag(takes_context=True)
def voting_form_field_errors(context, award):
    errors = context['form'].errors.get('award_%s' % award.pk)
    if errors:
        return format_html('<div class="alert alert-danger">{}</div>', errors)
    else:
        return ''

@register.simple_tag(takes_context=True)
def voting_form_field(context, award, nomination=None):
    return format_html(
        '<input type="radio" name="award_{}" value="{}"{}>',
        award.pk,
        nomination.pk if nomination else '',
        mark_safe(' checked="checked"') if not nomination and not context['form']['award_%s' % award.pk].value() or nomination and str(context['form']['award_%s' % award.pk].value()) in (str(nom.pk) for nom in nomination.nominations) else ''
    )

@register.simple_tag(takes_context=True)
def voting_form_errors(context):
    return format_html(
        '<dl class="errorlist">\n{}\n</dl>',
        format_html_join(
            '\n',
            '<dt><a href="#field-award_{}">{}</a></dt><dd>{}</dd>',
            ((
                context['form'].fields[field].award.pk,
                context['form'].fields[field].label,
                errors
            ) for field, errors in context['form'].errors.items())
        )
    )