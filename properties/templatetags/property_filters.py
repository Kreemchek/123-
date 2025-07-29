from django import template
import re

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

@register.filter
def replace(value, arg):
    """
    Replaces all occurrences of the first part of the argument with the second.
    The argument should be in the format "old,new".
    """
    old, new = arg.split(',')
    return value.replace(old, new)

@register.filter
def trim(value):
    """Удаляет начальные и конечные пробелы"""
    return value.strip()

@register.filter
def strip_metro(value):
    """Удаляет слово 'метро' и лишние пробелы из строки"""
    if not value:
        return value
    # Удаляем слово "метро" в разных вариациях
    value = re.sub(r'метро[, ]*', '', value, flags=re.IGNORECASE)
    # Удаляем лишние пробелы
    return value.strip()