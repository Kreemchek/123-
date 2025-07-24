from django import template

register = template.Library()

@register.filter
def space_format(value):
    return "{:,.0f}".format(value).replace(",", " ").replace(".", " ")

@register.filter
def get_type(value):
    return type(value).__name__



@register.filter
def replace_comma(value):
    """Заменяет запятую на точку в числе"""
    return str(value).replace(',', '.')