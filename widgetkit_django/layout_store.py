from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LayoutPlacement:
    widget_id: str
    sort_index: int
    x: int = 0
    y: int = 0
    w: int = 6
    h: int = 1
    config_json: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.widget_id.strip():
            raise ValueError("widget_id must not be empty")
        if self.sort_index < 0 or self.x < 0 or self.y < 0:
            raise ValueError("layout placement coordinates must be non-negative")
        if self.w < 1 or self.h < 1:
            raise ValueError("layout placement dimensions must be positive")
        if self.config_json is not None and not isinstance(self.config_json, dict):
            raise TypeError("config_json must be a dictionary or None")


@dataclass(frozen=True)
class LayoutState:
    """Distinguishes an absent saved layout from an explicitly empty one."""

    exists: bool
    placements: tuple[LayoutPlacement, ...] = ()

    def __post_init__(self) -> None:
        if not self.exists and self.placements:
            raise ValueError("a missing layout cannot contain placements")


class LayoutStore(Protocol):
    def load_layout(self, *, area_key: str, subpage_key: str, active_domain: str, owner: object | None) -> LayoutState:
        ...

    def load_shared_layout(self, *, area_key: str, subpage_key: str, active_domain: str) -> LayoutState:
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
        """Remove the saved override so the next load uses shared/default state."""
        ...
