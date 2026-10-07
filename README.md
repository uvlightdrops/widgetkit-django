# widgetkit-django

Reusable Django integration layer for widget-based dashboard and subpage layout builders.

## Status

This repository is the standalone home of `widgetkit_django`. It was extracted from `ki-knowledge` after the builder UI, persistence contract, registry contract, metadata layer, and controller logic were separated from app-specific code.

## What it provides

- typed host-supplied page-target contract and URL query helper
- a reusable dashboard builder controller
- reusable builder templates and static assets
- a layout persistence protocol
- a widget registry protocol
- reusable builder action handling
- reusable builder context assembly
- typed widget, page-target, layout-state, and preview-result contracts
- a reusable read-only catalog UI and preview sanitizer
- a shared twelve-column layout algorithm and stylesheet
- a Django template tag for URLs built from a host-resolved base URL

## Package layout

```text
widgetkit_django/
├── apps.py
├── builder.py
├── builder_actions.py
├── layout_store.py
├── layout.py
├── layout_targets.py
├── preview.py
├── registry.py
├── views.py
├── templates/widgetkit_django/
│   ├── base.html
│   ├── dashboard_builder.html
│   ├── dashboard_builder_shell.html
│   └── widget_catalog_content.html
├── static/widgetkit_django/
│   ├── css/dashboard-builder.css
│   ├── css/layout-grid.css
│   ├── css/widget-catalog.css
│   ├── js/dashboard-builder.js
│   └── js/widget-catalog.js
└── templatetags/widgetkit_django.py
```

## Architecture

The package is built around explicit registry, persistence, page-target, and preview contracts.

### Widget registry contract

Defined in `registry.py`.

Hosts provide:

- builtin areas
- widget hierarchy
- all widget IDs
- widget lookup by ID
- default widgets for an area/subpage

For simple integration, `CallbackWidgetRegistry` adapts host functions to the package contract.

### Layout store contract

Defined in `layout_store.py`. `LayoutState.exists` distinguishes a missing
layout (resolve shared/default state) from a saved empty layout (show no
widgets). `clear_placements` removes a saved override; replacing it with an
empty placement list intentionally persists an empty layout. Placement config,
height, and width are preserved when the order is updated.

Hosts provide placement loading and persistence through `LayoutStore` and `LayoutPlacement`.

### Page targets and preview results

`PageTarget` contains a host-supplied key, label, and URL. `BuilderViewConfig`
requires host callbacks for page targets and builder URLs; the package does not
know the host's routes, navigation, tenant/domain selection, or permissions.
`PreviewResult` is a typed serializable contract; host renderers provide the
sample content and scope label, while `readonly_preview_html` removes actions,
resources, event handlers, and unsafe markup.

### Builder controller config

Defined in `views.py`.

Hosts pass a `BuilderViewConfig` with:

- registry
- layout store
- active-domain lookup
- selection loading
- selection syncing
- route URL generation and page-target lookup
- optional scoped cache invalidation
- route/template options

## Main entry points

### `views.dashboard_builder_view`

Generic builder page/controller.

### `builder_actions.resolve_builder_action`

Generic persistence mutation and default-seeding logic for builder actions.

### `builder.build_dashboard_builder_context`

Generic page-context builder for the builder UI.

### `layout_targets.*`

Host-neutral `PageTarget`, its provider protocol, and `builder_url(base_url,
area, subpage)`. The host supplies navigation data and resolves route names.

## Host integration pattern

The host application supplies concrete adapters.

Typical host responsibilities:

- implement a `LayoutStore`
- expose a widget registry via `CallbackWidgetRegistry`
- decide how active domain/tenant is derived
- decide where selected widgets are cached in session
- wire the URL to a thin host view that calls `widgetkit_django.views.dashboard_builder_view`
- provide authorization at its URL/view boundary
- provide catalog sample data and widget renderers

## Templates

The default builder template extends `widgetkit_base_template`.

Default fallback:

- `widgetkit_django/base.html`

Host override:

- pass `base_template_name="base.html"` through `BuilderViewConfig`

This makes the package usable standalone while still fitting into a host site shell.

## Static assets

The package expects Django staticfiles to serve:

- `widgetkit_django/css/dashboard-builder.css`
- `widgetkit_django/css/layout-grid.css`
- `widgetkit_django/css/widget-catalog.css`
- `widgetkit_django/js/dashboard-builder.js`
- `widgetkit_django/js/widget-catalog.js`

Make sure the app is installed in `INSTALLED_APPS`.

## Host boundary

In a host project, `widgetkit_django` should stay generic and the host app should remain concrete.

Generic:

- builder UI
- builder controller
- generic page-target contract/helpers (not host navigation data)
- contracts
- catalog UI and read-only markup sanitation
- twelve-column grid mechanics

Concrete:

- actual widget catalog
- actual page targets/navigation and route names
- sample data and widget renderers
- actual database models
- actual domain/session behavior

The package treats `widget_id` as the persisted selection key. It does not
invent per-instance identity for placing the same widget more than once; hosts
that need duplicate instances should introduce a versioned placement identity
before enabling that behavior.

## Project docs

- host integration: `docs/host-integration.md`
- packaging roadmap: `docs/packaging-roadmap.md`
- extraction log: `docs/extraction-log.md`
