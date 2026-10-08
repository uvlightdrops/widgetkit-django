"""Host-neutral table query parsing and toolbar view models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlencode


@dataclass(frozen=True)
class ChoiceFilter:
    key: str
    label: str
    options: tuple[tuple[str, str], ...]
    all_label: str = "Alle"

    def clean(self, value: Any) -> str:
        candidate = str(value or "").strip()
        return candidate if candidate in {key for key, _label in self.options} else ""

    def label_for(self, value: str) -> str:
        if not value:
            return self.all_label
        return dict(self.options).get(value, value)


@dataclass(frozen=True)
class TextFilter:
    key: str
    label: str
    max_length: int = 200
    placeholder: str = ""

    def clean(self, value: Any) -> str:
        return str(value or "").strip()[: max(0, int(self.max_length))]


@dataclass(frozen=True)
class SortOption:
    key: str
    label: str


@dataclass(frozen=True)
class TableSpec:
    filters: tuple[ChoiceFilter | TextFilter, ...]
    sorts: tuple[SortOption, ...]
    default_sort: str
    page_param: str = "page"
    choice_params: tuple[ChoiceFilter, ...] = ()


@dataclass(frozen=True)
class TablePreset:
    key: str
    label: str
    params: Mapping[str, str]


@dataclass(frozen=True)
class FacetOption:
    value: str
    label: str
    count: int
    active: bool
    href: str


@dataclass(frozen=True)
class PresetLink:
    key: str
    label: str
    active: bool
    href: str
    count: int | None = None


@dataclass(frozen=True)
class SortLink:
    key: str
    label: str
    active: bool
    href: str


@dataclass(frozen=True)
class TablePage:
    items: tuple[Any, ...]
    total: int
    first_index: int
    last_index: int
    prev_href: str
    next_href: str


@dataclass(frozen=True)
class TableQuery:
    spec: TableSpec
    values: Mapping[str, str]
    page: int

    def url(self, base_url: str, **overrides: str | int | None) -> str:
        values = dict(self.values)
        page = self.page
        for key, value in overrides.items():
            if key == self.spec.page_param:
                page = _clean_page(value)
            elif value is None:
                values.pop(key, None)
            else:
                values[key] = str(value)
        values = _clean_values(self.spec, values)
        query: dict[str, str] = {}
        for item in self.spec.filters:
            value = values.get(item.key, "")
            if value:
                query[item.key] = value
        sort = values.get("sort", self.spec.default_sort)
        if sort and sort != self.spec.default_sort:
            query["sort"] = sort
        for item in self.spec.choice_params:
            value = values.get(item.key, "")
            default = item.options[0][0] if item.options else ""
            if value and value != default:
                query[item.key] = value
        if page > 1:
            query[self.spec.page_param] = str(page)
        encoded = urlencode(query)
        return f"{base_url}?{encoded}" if encoded else base_url

    def hidden_items(self) -> tuple[tuple[str, str], ...]:
        items: list[tuple[str, str]] = []
        for item in self.spec.filters:
            value = self.values.get(item.key, "")
            if value:
                items.append((item.key, value))
        sort = self.values.get("sort", self.spec.default_sort)
        if sort and sort != self.spec.default_sort:
            items.append(("sort", sort))
        for item in self.spec.choice_params:
            value = self.values.get(item.key, "")
            default = item.options[0][0] if item.options else ""
            if value and value != default:
                items.append((item.key, value))
        return tuple(items)


def parse_table_query(spec: TableSpec, params: Any) -> TableQuery:
    raw = {key: _get_param(params, key) for key in _spec_keys(spec)}
    values = _clean_values(spec, raw)
    return TableQuery(spec=spec, values=values, page=_clean_page(_get_param(params, spec.page_param)))


def facet_options(spec: TableSpec, query: TableQuery, key: str, counts: Mapping[str, int], base_url: str) -> list[FacetOption]:
    choice = _choice_filter(spec, key)
    total = sum(int(value or 0) for value in counts.values())
    options = [FacetOption("", choice.all_label, total, not query.values.get(key), query.url(base_url, **{key: "", spec.page_param: 1}))]
    for value, label in choice.options:
        options.append(FacetOption(
            value=value,
            label=label,
            count=int(counts.get(value, 0) or 0),
            active=query.values.get(key, "") == value,
            href=query.url(base_url, **{key: value, spec.page_param: 1}),
        ))
    return options


def preset_links(spec: TableSpec, query: TableQuery, presets: Sequence[TablePreset], base_url: str, counts: Mapping[str, int] | None = None) -> list[PresetLink]:
    ignored = {"sort", spec.page_param, *(item.key for item in spec.choice_params)}
    links: list[PresetLink] = []
    for preset in presets:
        overrides = {item.key: "" for item in spec.filters}
        overrides.update({key: str(value) for key, value in preset.params.items()})
        overrides[spec.page_param] = "1"
        active = all(
            query.values.get(item.key, "") == str(preset.params.get(item.key, "") or "")
            for item in spec.filters
            if item.key not in ignored
        )
        links.append(PresetLink(
            key=preset.key,
            label=preset.label,
            active=active,
            href=query.url(base_url, **overrides),
            count=None if counts is None else int(counts.get(preset.key, 0) or 0),
        ))
    return links


def sort_links(spec: TableSpec, query: TableQuery, base_url: str) -> list[SortLink]:
    return [
        SortLink(option.key, option.label, query.values.get("sort") == option.key, query.url(base_url, sort=option.key, **{spec.page_param: 1}))
        for option in spec.sorts
    ]


def paginate(items: Iterable[Any], query: TableQuery, page_size: int, base_url: str) -> TablePage:
    materialized = tuple(items)
    total = len(materialized)
    size = max(1, int(page_size))
    start = (query.page - 1) * size
    page_items = materialized[start : start + size]
    first = start + 1 if page_items else 0
    last = start + len(page_items) if page_items else 0
    prev_href = query.url(base_url, **{query.spec.page_param: query.page - 1}) if query.page > 1 else ""
    next_href = query.url(base_url, **{query.spec.page_param: query.page + 1}) if start + size < total else ""
    return TablePage(page_items, total, first, last, prev_href, next_href)


def _get_param(params: Any, key: str) -> str:
    getter = getattr(params, "get", None)
    return str(getter(key, "") if getter else "")


def _clean_page(value: Any) -> int:
    try:
        return max(1, int(str(value or "1")))
    except (TypeError, ValueError):
        return 1


def _spec_keys(spec: TableSpec) -> tuple[str, ...]:
    return tuple(item.key for item in spec.filters) + ("sort",) + tuple(item.key for item in spec.choice_params)


def _clean_values(spec: TableSpec, values: Mapping[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for item in spec.filters:
        cleaned[item.key] = item.clean(values.get(item.key, ""))
    sorts = {item.key for item in spec.sorts}
    selected_sort = str(values.get("sort", "") or "").strip()
    cleaned["sort"] = selected_sort if selected_sort in sorts else spec.default_sort
    for item in spec.choice_params:
        selected = item.clean(values.get(item.key, ""))
        cleaned[item.key] = selected or (item.options[0][0] if item.options else "")
    return cleaned


def _choice_filter(spec: TableSpec, key: str) -> ChoiceFilter:
    for item in spec.filters:
        if isinstance(item, ChoiceFilter) and item.key == key:
            return item
    raise KeyError(key)
