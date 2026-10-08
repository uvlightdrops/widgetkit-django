# Host integration

`widgetkit_django` owns reusable builder/catalog mechanics. The host owns
routes, navigation, persistence models, authorization, domain/tenant selection,
sample data, and widget renderers.

## Install and discover package resources

Install `widgetkit-django` and add `widgetkit_django` to `INSTALLED_APPS`. This
registers its templates, static assets, and template tags. Wheel builds include
the `templatetags` package as well as templates and static files.

## Registry and layout store

Implement `WidgetRegistry` and `LayoutStore`, or adapt callbacks with
`CallbackWidgetRegistry`. Registry entries structurally implement
`WidgetMetadata` (stable `widget_id`, area/category, label/description,
default dimensions, minimum width, and resize capability).

Layout stores implement `load_layout` and `load_shared_layout`, returning a
`LayoutState` with both `exists` and placements. The distinction is observable:

- Missing layout: use shared layout, then host defaults.
- Existing layout with placements: use those placements.
- Existing layout with zero placements: intentionally render an empty layout.
- `clear_placements`: remove the saved override so a future load resolves
  shared/default state again.
- `replace_placements(..., placements=[])`: explicitly save an empty layout.

`LayoutPlacement.config_json`, width, height, and grid coordinates are part of
the contract. The package preserves config and dimensions for surviving widget
IDs on order updates. The shared `layout_positions_for_widgets` helper provides
the package's twelve-column row-major placement algorithm.

## Builder view

Build `BuilderViewConfig` with:

- registry and store adapters
- active-scope getter
- selection loader/syncer
- `builder_url(area, subpage)` callback that returns a URL resolved by the host
- `page_targets_for_area(area)` callback returning `PageTarget` values
- optional `invalidate_layout_cache(area, subpage, active_scope)` callback
- optional host base template and presentation strings

Wire `dashboard_builder_view(request, config=...)` from a thin host view. The
controller accepts GET/POST only. Invalid area/page targets, actions, JSON
payloads, and widget IDs return HTTP 400; unsupported HTTP methods return 405.
The action contract is `add`, `remove`, `save-order`, and `reset`. Reset removes
the saved override; an empty `save-order` deliberately persists an empty
layout. A host cache invalidator receives only the changed area, subpage, and
active scope; the package never clears a global cache.

Authorization remains the host's responsibility: protect its URL/view with the
host's established authentication and permission policy.


## Table query and toolbar

`widgetkit_django.table` provides host-neutral contracts for table URL state:
`ChoiceFilter`, `TextFilter`, `SortOption`, `TableSpec`, `TablePreset`, and
`TableQuery`. The package validates query parameters against explicit allowlists,
emits canonical URLs with non-default parameters, builds facet/preset/sort links,
and slices pages with `paginate`.

The reusable `widgetkit_django/table_toolbar.html` template and
`widgetkit_django/css/data-table.css` render filter chips, shortcut presets, text
search, display choices, and sort controls with standalone fallback colors. Hosts
still own rows, counts, authorization, mutations, row rendering, and action URLs.
The toolbar must receive host-computed counts and links from the table helpers;
package code never reads host data or performs actions.

## Catalog and preview

The reusable catalog template expects area tabs with host-generated `url`,
`label`, `key`, and global `count`, metadata implementing `WidgetMetadata`, and
`PreviewResult.to_payload()` values. Hosts must create bounded sample context
and use their real widget fragment renderers; the package does not call live
data adapters. `readonly_preview_html` sanitizes rendered markup before it is
placed in the catalog. Provide `scope_label` (for example, “Domain” or
“Workspace”) with the preview result rather than relying on package-specific
terminology.

## Template URL tag

The package tag is host-neutral:

```django
{% load widgetkit_django %}
{% widgetkit_builder_url builder_base_url 'reports' 'overview' %}
```

The host resolves `builder_base_url`; the package only appends encoded area and
subpage query parameters. Host-specific convenience tags may wrap this helper.

## Layout grid CSS

Load `widgetkit_django/css/layout-grid.css` and put `widgetkit-grid--12` on the
grid with `widgetkit-grid__item` on each item. Set `--widgetkit-width` to the
persisted width. The stylesheet uses standalone fallback colors and does not
require a host theme or framework.
