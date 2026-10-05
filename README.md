# widgetkit-django

Reusable Django integration layer for widget-based dashboard and subpage layout builders.

## Status

This repository is the standalone home of `widgetkit_django`. It was extracted from `ki-knowledge` after the builder UI, persistence contract, registry contract, metadata layer, and controller logic were separated from app-specific code.

## What it provides

- shared area/subpage metadata for navigation and builder targets
- a reusable dashboard builder controller
- reusable builder templates and static assets
- a layout persistence protocol
- a widget registry protocol
- reusable builder action handling
- reusable builder context assembly
- a Django template tag for builder URLs

## Package layout

```text
widgetkit_django/
├── apps.py
├── builder.py
├── builder_actions.py
├── layout_store.py
├── layout_targets.py
├── registry.py
├── views.py
├── templates/widgetkit_django/
│   ├── base.html
│   ├── dashboard_builder.html
│   └── dashboard_builder_shell.html
├── static/widgetkit_django/
│   ├── css/dashboard-builder.css
│   └── js/dashboard-builder.js
└── templatetags/widgetkit_django.py
```

## Architecture

The package is built around three explicit contracts.

### 1. Widget registry contract

Defined in `registry.py`.

Hosts provide:

- builtin areas
- widget hierarchy
- all widget IDs
- widget lookup by ID
- default widgets for an area/subpage

For simple integration, `CallbackWidgetRegistry` adapts host functions to the package contract.

### 2. Layout store contract

Defined in `layout_store.py`.

Hosts provide placement loading and persistence through `LayoutStore` and `LayoutPlacement`.

### 3. Builder controller config

Defined in `views.py`.

Hosts pass a `BuilderViewConfig` with:

- registry
- layout store
- active-domain lookup
- selection loading
- selection syncing
- route/template options

## Main entry points

### `views.dashboard_builder_view`

Generic builder page/controller.

### `builder_actions.resolve_builder_action`

Generic persistence mutation and default-seeding logic for builder actions.

### `builder.build_dashboard_builder_context`

Generic page-context builder for the builder UI.

### `layout_targets.*`

Shared metadata helpers for:

- area/subpage tabs
- target URLs
- navigation menus

## Host integration pattern

The host application should keep only concrete adapters.

Typical host responsibilities:

- implement a `LayoutStore`
- expose a widget registry via `CallbackWidgetRegistry`
- decide how active domain/tenant is derived
- decide where selected widgets are cached in session
- wire the URL to a thin host view that calls `widgetkit_django.views.dashboard_builder_view`

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
- `widgetkit_django/js/dashboard-builder.js`

Make sure the app is installed in `INSTALLED_APPS`.

## Host boundary

In a host project, `widgetkit_django` should stay generic and the host app should remain concrete.

Generic:

- builder UI
- builder controller
- metadata
- contracts

Concrete:

- actual widget catalog
- actual database models
- actual domain/session behavior

## Project docs

- host integration: `docs/host-integration.md`
- packaging roadmap: `docs/packaging-roadmap.md`
- extraction log: `docs/extraction-log.md`
