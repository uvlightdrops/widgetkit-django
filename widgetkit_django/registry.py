from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class WidgetRegistry(Protocol):
    def builtin_areas(self) -> list[str]:
        ...

    def widget_hierarchy(self) -> dict[str, Any]:
        ...

    def widget_ids(self) -> list[str]:
        ...

    def widget_by_id(self, widget_id: str) -> Any | None:
        ...

    def default_widget_ids_for_area(self, area_key: str, subpage_key: str | None = None) -> list[str]:
        ...


@dataclass(frozen=True)
class CallbackWidgetRegistry:
    builtin_areas_fn: Callable[[], list[str]]
    widget_hierarchy_fn: Callable[[], dict[str, Any]]
    widget_ids_fn: Callable[[], list[str]]
    widget_by_id_fn: Callable[[str], Any | None]
    default_widget_ids_for_area_fn: Callable[[str, str | None], list[str]]

    def builtin_areas(self) -> list[str]:
        return list(self.builtin_areas_fn())

    def widget_hierarchy(self) -> dict[str, Any]:
        return self.widget_hierarchy_fn()

    def widget_ids(self) -> list[str]:
        return list(self.widget_ids_fn())

    def widget_by_id(self, widget_id: str) -> Any | None:
        return self.widget_by_id_fn(widget_id)

    def default_widget_ids_for_area(self, area_key: str, subpage_key: str | None = None) -> list[str]:
        return list(self.default_widget_ids_for_area_fn(area_key, subpage_key))
