from datetime import datetime

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def astro_chart_url():
    return settings.ASTRO_CLOCK_SERVER.rstrip("/")


@register.filter
def parse_iso(value):
    if not value:
        return value
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return value
