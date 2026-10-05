from __future__ import annotations

from django import template

from widgetkit_django.layout_targets import layout_builder_url as build_layout_builder_url

register = template.Library()


@register.simple_tag
def layout_builder_url(area_key: str, subpage_key: str = "overview") -> str:
    return build_layout_builder_url(area_key, subpage_key)
