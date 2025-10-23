from django import template

register = template.Library()

@register.filter
def space_format(value):
    return "{:,.0f}".format(value).replace(",", " ").replace(".", " ")

@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def space_format(value):
    """
    Форматирует число с пробелами в качестве разделителей тысяч.
    """
    if value is None:
        return ""

    try:
        # Преобразуем в число
        num_value = float(value)

        # Форматируем как целое число
        return "{:,.0f}".format(num_value).replace(",", " ")

    except (ValueError, TypeError):
        # Если ошибка, возвращаем исходное значение
        return str(value)