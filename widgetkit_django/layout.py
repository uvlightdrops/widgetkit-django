from __future__ import annotations

from collections.abc import Callable, Iterable

from widgetkit_django.registry import WidgetMetadata


def layout_positions_for_widgets(
    widget_ids: Iterable[str],
    *,
    widget_by_id: Callable[[str], WidgetMetadata | None],
    columns: int = 12,
    widths: dict[str, int] | None = None,
) -> dict[str, dict[str, int]]:
    """Pack widgets row-major, using registry dimensions within a shared grid."""
    if columns < 1:
        raise ValueError("columns must be a positive integer")
    positions: dict[str, dict[str, int]] = {}
    current_x = current_y = 0
    for widget_id in widget_ids:
        spec = widget_by_id(widget_id)
        width = min(max((widths or {}).get(widget_id, spec.default_w if spec else 6), 1), columns)
        height = max(spec.default_h if spec else 1, 1)
        if current_x + width > columns:
            current_x = 0
            current_y += 1
        positions[widget_id] = {"x": current_x, "y": current_y, "w": width, "h": height}
        current_x += width
        if current_x >= columns:
            current_x = 0
            current_y += 1
    return positions
