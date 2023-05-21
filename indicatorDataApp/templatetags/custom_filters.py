from django import template

register = template.Library()

@register.filter
def class_name_filter(obj):
    return obj.__class__.__name__
