from __future__ import annotations

from typing import Callable

from widgetkit_django.layout_store import LayoutPlacement, LayoutStore
from widgetkit_django.registry import WidgetMetadata


def resolve_builder_action(
    action: str,
    *,
    store: LayoutStore,
    area_key: str,
    subpage_key: str,
    active_domain: str,
    owner: object | None,
    title: str,
    widget_id: str | None,
    widget_order: list[str] | None,
    widget_sizes: dict[str, int] | None,
    canonical_widget_id: Callable[[str], str],
    widget_by_id: Callable[[str], WidgetMetadata | None],
    default_widget_ids_for_area: Callable[[str, str | None], list[str]],
    layout_positions_for_widgets: Callable[..., dict[str, dict[str, int]]],
) -> list[str]:
    """Apply add/remove/reset/reorder mutations without discarding placement config."""
    normalized_action = (action or "").strip()
    if normalized_action not in {"add", "remove", "reset", "save-order"}:
        raise ValueError("Unsupported layout action")

    if normalized_action == "reset":
        store.clear_placements(
            area_key=area_key, subpage_key=subpage_key, active_domain=active_domain,
            owner=owner, title=title,
        )
        if owner is not None:
            shared = store.load_shared_layout(
                area_key=area_key, subpage_key=subpage_key, active_domain=active_domain,
            )
            if shared.exists:
                return list(dict.fromkeys(
                    canonical_widget_id(item.widget_id)
                    for item in sorted(shared.placements, key=lambda item: item.sort_index)
                    if widget_by_id(canonical_widget_id(item.widget_id)) is not None
                ))
        return [
            canonical_widget_id(candidate)
            for candidate in default_widget_ids_for_area(area_key, subpage_key)
            if widget_by_id(canonical_widget_id(candidate)) is not None
        ]

    layout = store.load_layout(
        area_key=area_key, subpage_key=subpage_key, active_domain=active_domain, owner=owner,
    )
    if not layout.exists and owner is not None:
        shared = store.load_shared_layout(
            area_key=area_key, subpage_key=subpage_key, active_domain=active_domain,
        )
        if shared.exists:
            layout = shared
    existing = {
        canonical_widget_id(placement.widget_id): placement
        for placement in layout.placements
        if widget_by_id(canonical_widget_id(placement.widget_id)) is not None
    }
    if layout.exists:
        selections = sorted(existing, key=lambda key: existing[key].sort_index)
    else:
        selections = [
            canonical_widget_id(candidate)
            for candidate in default_widget_ids_for_area(area_key, subpage_key)
            if widget_by_id(canonical_widget_id(candidate)) is not None
        ]

    requested_widths: dict[str, int] = {}
    if widget_sizes is not None:
        for raw_id, width in widget_sizes.items():
            normalized_id = canonical_widget_id(raw_id)
            spec = widget_by_id(normalized_id)
            if spec is None:
                raise ValueError(f"Unknown widget in width map: {raw_id}")
            requested_widths[normalized_id] = _clamp_width(spec, width)

    if normalized_action == "add":
        if not widget_id:
            raise ValueError("widget_id is required for add")
        normalized_id = canonical_widget_id(widget_id)
        if widget_by_id(normalized_id) is None:
            raise ValueError(f"Unknown widget: {widget_id}")
        if normalized_id not in selections:
            selections.append(normalized_id)
    elif normalized_action == "remove":
        if not widget_id:
            raise ValueError("widget_id is required for remove")
        normalized_id = canonical_widget_id(widget_id)
        if widget_by_id(normalized_id) is None:
            raise ValueError(f"Unknown widget: {widget_id}")
        selections = [selected for selected in selections if selected != normalized_id]
    else:
        if widget_order is None:
            raise ValueError("widget_order is required for save-order")
        selections = []
        seen: set[str] = set()
        for candidate in widget_order:
            normalized_id = canonical_widget_id(str(candidate).strip())
            if not normalized_id:
                raise ValueError("widget_order contains an empty widget ID")
            if normalized_id in seen:
                raise ValueError(f"widget_order contains duplicate widget: {normalized_id}")
            if widget_by_id(normalized_id) is None:
                raise ValueError(f"Unknown widget: {candidate}")
            seen.add(normalized_id)
            selections.append(normalized_id)

    widths = {
        selected: requested_widths.get(
            selected,
            _clamp_width(widget_by_id(selected), existing[selected].w)
            if selected in existing else _default_width(widget_by_id(selected)),
        )
        for selected in selections
    }
    positions = layout_positions_for_widgets(selections, widths=widths)
    placements = []
    for index, selected_id in enumerate(selections):
        spec = widget_by_id(selected_id)
        previous = existing.get(selected_id)
        placements.append(LayoutPlacement(
            widget_id=selected_id,
            sort_index=index,
            x=positions[selected_id]["x"],
            y=positions[selected_id]["y"],
            w=widths[selected_id],
            h=previous.h if previous is not None else max(spec.default_h if spec else 1, 1),
            config_json=previous.config_json if previous is not None else None,
        ))
    store.replace_placements(
        area_key=area_key, subpage_key=subpage_key, active_domain=active_domain,
        owner=owner, title=title, placements=placements,
    )
    return selections


def _default_width(spec: WidgetMetadata | None) -> int:
    if spec is None:
        return 6
    return _clamp_width(spec, spec.default_w)


def _clamp_width(spec: WidgetMetadata | None, requested: int) -> int:
    minimum = max(1, min(int(spec.min_w) if spec else 3, 12))
    default = int(spec.default_w) if spec else 6
    if spec is not None and not spec.resizable:
        return max(minimum, min(default, 12))
    return max(minimum, min(int(requested), 12))
