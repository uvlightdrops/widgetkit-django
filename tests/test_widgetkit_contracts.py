from dataclasses import dataclass

import pytest

from widgetkit_django.builder import placement_map_for_builder
from widgetkit_django.builder_actions import resolve_builder_action
from widgetkit_django.layout import layout_positions_for_widgets
from widgetkit_django.layout_store import LayoutPlacement, LayoutState
from widgetkit_django.layout_targets import PageTarget, builder_url
from widgetkit_django.preview import PreviewResult, readonly_preview_html


@dataclass(frozen=True)
class Widget:
    widget_id: str
    area: str = "reports"
    category: str = "overview"
    label: str = "Report"
    description: str = "A report"
    default_size: str = "wide"
    default_w: int = 8
    min_w: int = 4
    default_h: int = 1
    resizable: bool = True


class Store:
    def __init__(self, layout: LayoutState):
        self.layout = layout
        self.replaced = None

    def load_layout(self, **kwargs):
        return self.layout

    def load_shared_layout(self, **kwargs):
        return LayoutState(exists=False)

    def load_placements(self, **kwargs):
        return list(self.layout.placements)

    def load_shared_placements(self, **kwargs):
        return []

    def replace_placements(self, *, placements, **kwargs):
        self.replaced = placements
        self.layout = LayoutState(exists=True, placements=tuple(placements))

    def clear_placements(self, **kwargs):
        self.layout = LayoutState(exists=False)


WIDGETS = {
    "reports.one": Widget("reports.one", default_w=8),
    "reports.two": Widget("reports.two", default_w=6),
}


def resolve(store, action, *, widget_order=None, widget_sizes=None, widget_id=None):
    return resolve_builder_action(
        action,
        store=store,
        area_key="reports",
        subpage_key="overview",
        active_domain="tenant-a",
        owner="user-1",
        title="Reports",
        widget_id=widget_id,
        widget_order=widget_order,
        widget_sizes=widget_sizes,
        canonical_widget_id=lambda value: "reports.one" if value == "legacy.one" else value,
        widget_by_id=WIDGETS.get,
        default_widget_ids_for_area=lambda area, page: ["reports.one", "reports.two"],
        layout_positions_for_widgets=lambda ids, widths=None: layout_positions_for_widgets(
            ids, widget_by_id=WIDGETS.get, widths=widths,
        ),
    )


def test_contract_types_and_generic_builder_url():
    target = PageTarget("overview", "Overview", "/reports/")
    preview = PreviewResult(
        widget_id="reports.one", label="Report", description="A report",
        area="reports", category="overview", width=8, height=1,
        active_domain="tenant-a", preview_mode="sample", readonly=True,
        status="sample", note="", body_html="<p>Example</p>",
    )
    assert target.path == "/reports/"
    assert preview.to_payload()["readonly"] is True
    assert builder_url("/builder/", "reports", "overview") == (
        "/builder/?area=reports&subpage=overview"
    )


def test_grid_positions_use_a_twelve_column_shared_layout():
    positions = layout_positions_for_widgets(
        ["reports.one", "reports.two"], widget_by_id=WIDGETS.get,
    )
    assert positions == {
        "reports.one": {"x": 0, "y": 0, "w": 8, "h": 1},
        "reports.two": {"x": 0, "y": 1, "w": 6, "h": 1},
    }


def test_save_order_preserves_custom_width_and_config_json():
    store = Store(LayoutState(exists=True, placements=(
        LayoutPlacement(
            "reports.one", 0, x=0, y=0, w=5, h=3,
            config_json={"view": "compact"},
        ),
        LayoutPlacement("reports.two", 1, x=5, y=0, w=7, h=2, config_json={"sort": "date"}),
    )))
    assert resolve(
        store, "save-order",
        widget_order=["reports.two", "reports.one"],
    ) == ["reports.two", "reports.one"]
    placements = store.replaced
    assert [(item.widget_id, item.w, item.h, item.config_json) for item in placements] == [
        ("reports.two", 7, 2, {"sort": "date"}),
        ("reports.one", 5, 3, {"view": "compact"}),
    ]
    assert placements[0].x == 0
    assert placements[1].x == 7


def test_explicit_empty_layout_does_not_reseed_defaults():
    store = Store(LayoutState(exists=True, placements=()))
    assert resolve(store, "add", widget_id="reports.two") == ["reports.two"]
    assert [item.widget_id for item in store.replaced] == ["reports.two"]


def test_builder_uses_shared_dimensions_only_when_personal_layout_is_missing():
    shared = LayoutState(exists=True, placements=(
        LayoutPlacement("reports.one", 0, w=5, h=2, config_json={"view": "shared"}),
    ))

    class SharedStore(Store):
        def load_shared_layout(self, **kwargs):
            return shared

    missing_map = placement_map_for_builder(
        store=SharedStore(LayoutState(exists=False)),
        area_key="reports", subpage_key="overview",
        active_domain="tenant-a", owner="user-1",
    )
    assert missing_map["reports.one"].w == 5

    empty_map = placement_map_for_builder(
        store=SharedStore(LayoutState(exists=True)),
        area_key="reports", subpage_key="overview",
        active_domain="tenant-a", owner="user-1",
    )
    assert empty_map == {}


def test_missing_layout_seeds_defaults_and_reset_removes_override():
    store = Store(LayoutState(exists=False))
    assert resolve(store, "add", widget_id="reports.two") == ["reports.one", "reports.two"]
    assert resolve(store, "reset") == ["reports.one", "reports.two"]
    assert store.layout.exists is False


def test_invalid_actions_and_widget_ids_are_explicit_errors():
    store = Store(LayoutState(exists=True))
    with pytest.raises(ValueError, match="Unsupported"):
        resolve(store, "delete")
    with pytest.raises(ValueError, match="Unknown widget"):
        resolve(store, "add", widget_id="reports.unknown")


def test_preview_sanitizer_removes_resources_forms_and_scripts():
    html = readonly_preview_html(
        '<script>bad()</script><form action="/post"><input name="x">'
        '<button onclick="bad()">Submit</button></form>'
        '<a href="javascript:bad()">Open</a><p>Safe &amp; useful</p>'
    )
    assert "bad()" not in html
    assert "/post" not in html
    assert "name=" not in html
    assert "href=" not in html
    assert 'disabled' in html
    assert "Safe &amp; useful" in html


def test_alias_removal_and_addition_use_canonical_identity():
    saved = LayoutState(exists=True, placements=(
        LayoutPlacement("legacy.one", 0, w=5, config_json={"view": "compact"}),
    ))
    store = Store(saved)
    assert resolve(store, "add", widget_id="reports.one") == ["reports.one"]
    assert len(store.replaced) == 1
    assert store.replaced[0].w == 5
    assert store.replaced[0].config_json == {"view": "compact"}
    store = Store(saved)
    assert resolve(store, "remove", widget_id="reports.one") == []


def test_builder_resolves_alias_placement_dimensions():
    class Registry:
        def widget_by_id(self, widget_id):
            return WIDGETS.get("reports.one" if widget_id == "legacy.one" else widget_id)

    placements = placement_map_for_builder(
        store=Store(LayoutState(exists=True, placements=(
            LayoutPlacement("legacy.one", 0, w=5),
        ))),
        registry=Registry(),
        area_key="reports", subpage_key="overview",
        active_domain="tenant-a", owner="user-1",
    )
    assert placements["reports.one"].w == 5


@pytest.mark.parametrize("placements, expected", [
    ((), []),
    ((LayoutPlacement("legacy.one", 0, w=5),), ["reports.one"]),
])
def test_reset_returns_effective_shared_layout(placements, expected):
    class SharedStore(Store):
        def load_shared_layout(self, **kwargs):
            return LayoutState(exists=True, placements=placements)

    store = SharedStore(LayoutState(exists=True))
    assert resolve(store, "reset") == expected
    assert store.layout.exists is False
