from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from widgetkit_django.builder import build_dashboard_builder_context, placement_map_for_builder
from widgetkit_django.registry import WidgetRegistry


@dataclass(frozen=True)
class BuilderViewConfig:
    registry: WidgetRegistry
    layout_store: object
    active_domain_getter: Callable[[HttpRequest], str]
    selection_loader: Callable[[HttpRequest, str, str, list[str]], list[str]]
    selection_syncer: Callable[[HttpRequest, str], list[str]]
    builder_url_name: str = "settings-layout-builder"
    page_template: str = "widgetkit_django/dashboard_builder.html"
    shell_template: str = "widgetkit_django/dashboard_builder_shell.html"
    base_template_name: str = "widgetkit_django/base.html"
    default_area_key: str = "settings"
    default_subpage_key: str = "overview"
    page_title: str = "Dashboard Builder"
    page_subtitle: str = "Drag widgets into the grid, drop them to the unused stash to park them, or switch the area to move a layout to another subpage."


def dashboard_builder_view(request: HttpRequest, *, config: BuilderViewConfig):
    active_domain = config.active_domain_getter(request)
    area_key = request.GET.get("area", request.POST.get("area", config.default_area_key)).strip() or config.default_area_key
    subpage_key = request.GET.get("subpage", request.POST.get("subpage", config.default_subpage_key)).strip().lower() or config.default_subpage_key
    if area_key not in set(config.registry.builtin_areas()):
        area_key = config.default_area_key

    if request.method == "POST":
        selected_widget_ids = config.selection_syncer(request, area_key)
        cache.clear()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "ok": True,
                    "selected_widget_ids": selected_widget_ids,
                    "area_key": area_key,
                    "subpage_key": subpage_key,
                }
            )
    else:
        fallback = config.registry.default_widget_ids_for_area(area_key, subpage_key)
        selected_widget_ids = config.selection_loader(request, area_key, subpage_key, fallback)

    owner = request.user if getattr(request.user, "is_authenticated", False) else None
    placement_by_widget = placement_map_for_builder(
        store=config.layout_store,
        area_key=area_key,
        subpage_key=subpage_key,
        active_domain=active_domain,
        owner=owner,
    )
    context = build_dashboard_builder_context(
        active_domain=active_domain,
        area_key=area_key,
        subpage_key=subpage_key,
        registry=config.registry,
        selected_widget_ids=selected_widget_ids,
        placement_by_widget=placement_by_widget,
        builder_url_name=config.builder_url_name,
        page_title=config.page_title,
        page_subtitle=config.page_subtitle,
        base_template_name=config.base_template_name,
    )
    if request.headers.get("HX-Request") == "true":
        return render(request, config.shell_template, context)
    return render(request, config.page_template, context)
