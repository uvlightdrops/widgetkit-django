from __future__ import annotations

from django import template

from widgetkit_django.layout_targets import builder_url

register = template.Library()


@register.simple_tag
def widgetkit_builder_url(base_url: str, area_key: str, subpage_key: str = "overview") -> str:
    return builder_url(base_url, area_key, subpage_key)
