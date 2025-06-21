from django import template


register = template.Library()

@register.filter
def subtract(value, arg):
    """Soustrait arg à value"""
    return value - arg


register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


