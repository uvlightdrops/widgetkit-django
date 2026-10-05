from __future__ import annotations

from typing import Any, Callable

from widgetkit_django.layout_store import LayoutPlacement, LayoutStore


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
    widget_by_id: Callable[[str], Any | None],
    default_widget_ids_for_area: Callable[[str, str | None], list[str]],
    layout_positions_for_widgets: Callable[[list[str]], dict[str, dict[str, int]]],
) -> list[str]:
    def _resolved_width(selected_widget_id: str, fallback_width: int) -> int:
        spec = widget_by_id(selected_widget_id)
        default_width = int(getattr(spec, "default_w", fallback_width) if spec is not None else fallback_width)
        min_width = max(3, min(int(getattr(spec, "min_w", 3) if spec is not None else 3), 12))
        is_resizable = bool(getattr(spec, "resizable", True)) if spec is not None else True
        requested_width = widget_sizes.get(selected_widget_id, default_width) if widget_sizes else default_width
        if not is_resizable:
            return max(min_width, min(default_width, 12))
        return max(min_width, min(int(requested_width), 12))

    selections = [canonical_widget_id(item.widget_id) for item in store.load_placements(
        area_key=area_key,
        subpage_key=subpage_key,
        active_domain=active_domain,
        owner=owner,
    )]
    if not selections:
        shared = store.load_shared_placements(area_key=area_key, subpage_key=subpage_key, active_domain=active_domain)
        if shared:
            seeded = [
                LayoutPlacement(
                    widget_id=canonical_widget_id(item.widget_id),
                    sort_index=item.sort_index,
                    x=item.x,
                    y=item.y,
                    w=item.w,
                    h=item.h,
                    config_json=item.config_json,
                )
                for item in shared
                if widget_by_id(canonical_widget_id(item.widget_id)) is not None
            ]
            if seeded:
                store.replace_placements(
                    area_key=area_key,
                    subpage_key=subpage_key,
                    active_domain=active_domain,
                    owner=owner,
                    title=title,
                    placements=seeded,
                )
                selections = [item.widget_id for item in seeded]
        else:
            default_ids = [
                canonical_widget_id(candidate)
                for candidate in default_widget_ids_for_area(area_key, subpage_key)
                if widget_by_id(canonical_widget_id(candidate)) is not None
            ]
            positions = layout_positions_for_widgets(default_ids)
            store.replace_placements(
                area_key=area_key,
                subpage_key=subpage_key,
                active_domain=active_domain,
                owner=owner,
                title=title,
                placements=[
                    LayoutPlacement(
                        widget_id=candidate,
                        sort_index=index,
                        x=positions[candidate]["x"],
                        y=positions[candidate]["y"],
                        w=positions[candidate]["w"],
                        h=positions[candidate]["h"],
                    )
                    for index, candidate in enumerate(default_ids)
                ],
            )
            selections = list(default_ids)

    normalized_action = (action or "").strip()
    if normalized_action == "reset":
        store.clear_placements(
            area_key=area_key,
            subpage_key=subpage_key,
            active_domain=active_domain,
            owner=owner,
            title=title,
        )
        return []

    widget_id = canonical_widget_id(widget_id) if widget_id else None

    if normalized_action == "add" and widget_id:
        if widget_by_id(widget_id) is not None and widget_id not in selections:
            selections.append(widget_id)
            positions = layout_positions_for_widgets(selections)
            store.replace_placements(
                area_key=area_key,
                subpage_key=subpage_key,
                active_domain=active_domain,
                owner=owner,
                title=title,
                placements=[
                    LayoutPlacement(
                        widget_id=selected_widget_id,
                        sort_index=index,
                        w=_resolved_width(selected_widget_id, positions[selected_widget_id]["w"]),
                        h=positions[selected_widget_id]["h"],
                        x=positions[selected_widget_id]["x"],
                        y=positions[selected_widget_id]["y"],
                    )
                    for index, selected_widget_id in enumerate(selections)
                ],
            )
        return selections

    if normalized_action == "remove" and widget_id:
        selections = [selected_widget_id for selected_widget_id in selections if selected_widget_id != widget_id]
        positions = layout_positions_for_widgets(selections)
        store.replace_placements(
            area_key=area_key,
            subpage_key=subpage_key,
            active_domain=active_domain,
            owner=owner,
            title=title,
            placements=[
                LayoutPlacement(
                    widget_id=selected_widget_id,
                    sort_index=index,
                    w=_resolved_width(selected_widget_id, positions[selected_widget_id]["w"]),
                    h=positions[selected_widget_id]["h"],
                    x=positions[selected_widget_id]["x"],
                    y=positions[selected_widget_id]["y"],
                )
                for index, selected_widget_id in enumerate(selections)
            ],
        )
        return selections

    if normalized_action == "save-order":
        ordered = widget_order or []
        valid_ids: list[str] = []
        seen: set[str] = set()
        for candidate in ordered:
            item = canonical_widget_id(str(candidate).strip())
            if not item or item in seen or widget_by_id(item) is None:
                continue
            seen.add(item)
            valid_ids.append(item)
        positions = layout_positions_for_widgets(valid_ids)
        store.replace_placements(
            area_key=area_key,
            subpage_key=subpage_key,
            active_domain=active_domain,
            owner=owner,
            title=title,
            placements=[
                LayoutPlacement(
                    widget_id=selected_widget_id,
                    sort_index=index,
                    w=_resolved_width(selected_widget_id, positions[selected_widget_id]["w"]),
                    h=positions[selected_widget_id]["h"],
                    x=positions[selected_widget_id]["x"],
                    y=positions[selected_widget_id]["y"],
                )
                for index, selected_widget_id in enumerate(valid_ids)
            ],
        )
        return valid_ids

    return selections
