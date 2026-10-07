from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode


@dataclass(frozen=True)
class PageTarget:
    """A host-defined destination available to a builder area."""

    key: str
    label: str
    path: str


class PageTargetProvider(Protocol):
    def __call__(self, area_key: str) -> list[PageTarget]:
        ...


def builder_url(base_url: str, area_key: str, subpage_key: str = "overview") -> str:
    """Append builder selection parameters to a URL resolved by the host."""
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'area': area_key, 'subpage': subpage_key})}"
