from django import template
from accounts.models import SupportSettings

register = template.Library()

@register.simple_tag
def get_support_user():
    return SupportSettings.get_support_user()