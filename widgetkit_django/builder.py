from __future__ import annotations

from typing import Any

from widgetkit_django.layout_targets import PageTarget
from widgetkit_django.layout_store import LayoutPlacement, LayoutStore
from widgetkit_django.registry import WidgetRegistry


def build_dashboard_builder_context(
    *,
    active_domain: str,
    area_key: str,
    subpage_key: str,
    registry: WidgetRegistry,
    selected_widget_ids: list[str],
    placement_by_widget: dict[str, LayoutPlacement],
    page_title: str = "Dashboard Builder",
    page_subtitle: str = "Drag widgets into the grid, drop them to the unused stash to park them, or switch the area to move a layout to another subpage.",
    base_template_name: str = "widgetkit_django/base.html",
    page_targets: list[PageTarget] | None = None,
    area_tabs: list[dict[str, str]] | None = None,
    builder_action_url: str = "",
) -> dict[str, Any]:
    builtin_areas = registry.builtin_areas()
    widget_hierarchy = registry.widget_hierarchy()
    widget_ids = registry.widget_ids()
    widget_by_id = registry.widget_by_id
    selected_widget_meta = []
    width_options = {3, 4, 6, 8, 9, 12}
    for widget_id in selected_widget_ids:
        spec = widget_by_id(widget_id)
        if spec is None:
            continue
        placement = placement_by_widget.get(widget_id)
        width = placement.w if placement is not None else spec.default_w
        width_options.add(width)
        width_options.add(getattr(spec, "min_w", 3))
        selected_widget_meta.append({
            "spec": spec,
            "width": width,
            "min_width": getattr(spec, "min_w", 3),
            "resizable": getattr(spec, "resizable", True),
        })

    unused_widget_ids = [widget_id for widget_id in widget_ids if widget_id not in selected_widget_ids]
    unused_specs = [
        widget_by_id(widget_id)
        for widget_id in unused_widget_ids
        if widget_by_id(widget_id) is not None and widget_by_id(widget_id).area == area_key
    ]
    subpage_tabs = page_targets or []

    widget_area_entries = []
    for area in builtin_areas:
        area_tree = widget_hierarchy.get(area, {})
        category_entries = []
        for category_name, category_value in area_tree.items():
            if category_name == "_widgets":
                continue
            category_entries.append({
                "name": category_name,
                "widgets": category_value.get("_widgets", []),
            })
        widget_area_entries.append({
            "area": area,
            "categories": category_entries,
        })

    return {
        "active_domain": active_domain,
        "widget_area_entries": widget_area_entries,
        "selected_widgets": selected_widget_meta,
        "selected_widget_ids": selected_widget_ids,
        "unused_widgets": unused_specs,
        "area_key": area_key,
        "subpage_key": subpage_key,
        "builtin_areas": builtin_areas,
        "area_tabs": area_tabs or [
            {"key": area, "label": area.replace("_", " ").title(), "url": ""}
            for area in builtin_areas
        ],
        "subpage_tabs": subpage_tabs,
        "widget_width_options": sorted(width_options),
        "widgetkit_base_template": base_template_name,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "builder_action_url": builder_action_url,
        "dashboard_builder_config": {
            "emptyStateText": "No widgets selected for this area yet. Drag widgets from the unused pile into the grid.",
        },
    }


def placement_map_for_builder(
    *,
    store: LayoutStore,
    area_key: str,
    subpage_key: str,
    active_domain: str,
    owner: object | None,
    registry: WidgetRegistry | None = None,
) -> dict[str, LayoutPlacement]:
    layout = store.load_layout(
        area_key=area_key,
        subpage_key=subpage_key,
        active_domain=active_domain,
        owner=owner,
    )
    if layout.exists or owner is None:
        placements = layout.placements
    else:
        placements = store.load_shared_layout(
            area_key=area_key,
            subpage_key=subpage_key,
            active_domain=active_domain,
        ).placements
    result = {}
    for placement in placements:
        spec = registry.widget_by_id(placement.widget_id) if registry is not None else None
        key = spec.widget_id if spec is not None else placement.widget_id
        result[key] = placement
    return result
