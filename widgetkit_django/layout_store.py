from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LayoutPlacement:
    widget_id: str
    sort_index: int
    x: int = 0
    y: int = 0
    w: int = 6
    h: int = 1
    config_json: dict | None = None


class LayoutStore(Protocol):
    def load_placements(self, *, area_key: str, subpage_key: str, active_domain: str, owner: object | None) -> list[LayoutPlacement]:
        ...

    def load_shared_placements(self, *, area_key: str, subpage_key: str, active_domain: str) -> list[LayoutPlacement]:
        ...

    def replace_placements(
        self,
        *,
        area_key: str,
        subpage_key: str,
        active_domain: str,
        owner: object | None,
        title: str,
        placements: list[LayoutPlacement],
    ) -> None:
        ...

    def clear_placements(self, *, area_key: str, subpage_key: str, active_domain: str, owner: object | None, title: str) -> None:
        ...
