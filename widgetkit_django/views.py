from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render

from widgetkit_django.builder import build_dashboard_builder_context, placement_map_for_builder
from widgetkit_django.layout_targets import PageTarget, PageTargetProvider
from widgetkit_django.layout_store import LayoutStore
from widgetkit_django.registry import WidgetRegistry


@dataclass(frozen=True)
class BuilderViewConfig:
    registry: WidgetRegistry
    layout_store: LayoutStore
    active_domain_getter: Callable[[HttpRequest], str]
    selection_loader: Callable[[HttpRequest, str, str, list[str]], list[str]]
    selection_syncer: Callable[[HttpRequest, str], list[str]]
    builder_url: Callable[[str, str], str]
    page_targets_for_area: PageTargetProvider
    invalidate_layout_cache: Callable[[str, str, str], None] | None = None
    page_template: str = "widgetkit_django/dashboard_builder.html"
    shell_template: str = "widgetkit_django/dashboard_builder_shell.html"
    base_template_name: str = "widgetkit_django/base.html"
    default_area_key: str = "settings"
    default_subpage_key: str = "overview"
    page_title: str = "Dashboard Builder"
    page_subtitle: str = "Drag widgets into the grid, drop them to the unused stash to park them, or switch the area to move a layout to another subpage."


def dashboard_builder_view(request: HttpRequest, *, config: BuilderViewConfig):
    if request.method not in {"GET", "POST"}:
        return HttpResponseNotAllowed(["GET", "POST"])
    active_domain = config.active_domain_getter(request)
    area_key = request.GET.get("area", request.POST.get("area", config.default_area_key)).strip() or config.default_area_key
    subpage_key = request.GET.get("subpage", request.POST.get("subpage", config.default_subpage_key)).strip().lower() or config.default_subpage_key
    if area_key not in set(config.registry.builtin_areas()):
        return HttpResponseBadRequest("Unknown builder area")
    page_targets = config.page_targets_for_area(area_key)
    if page_targets and subpage_key not in {target.key for target in page_targets}:
        return HttpResponseBadRequest("Unknown builder page target")

    if request.method == "POST":
        try:
            selected_widget_ids = config.selection_syncer(request, area_key)
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        if config.invalidate_layout_cache is not None:
            config.invalidate_layout_cache(area_key, subpage_key, active_domain)
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
        registry=config.registry,
        area_key=area_key,
        subpage_key=subpage_key,
        active_domain=active_domain,
        owner=owner,
    )
    area_tabs = []
    for area in config.registry.builtin_areas():
        targets = config.page_targets_for_area(area)
        initial_target = next((target for target in targets if target.key == "overview"), None)
        if initial_target is None and targets:
            initial_target = targets[0]
        area_tabs.append({
            "key": area,
            "label": area.replace("_", " ").title(),
            "url": config.builder_url(area, initial_target.key if initial_target else "overview"),
        })
    context = build_dashboard_builder_context(
        active_domain=active_domain,
        area_key=area_key,
        subpage_key=subpage_key,
        registry=config.registry,
        selected_widget_ids=selected_widget_ids,
        placement_by_widget=placement_by_widget,
        page_title=config.page_title,
        page_subtitle=config.page_subtitle,
        base_template_name=config.base_template_name,
        page_targets=page_targets,
        area_tabs=area_tabs,
        builder_action_url=config.builder_url(area_key, subpage_key),
    )
    if request.headers.get("HX-Request") == "true":
        return render(request, config.shell_template, context)
    return render(request, config.page_template, context)
