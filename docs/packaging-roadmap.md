# Packaging status

The reusable Django package now builds as a standalone wheel. Setuptools
discovers the full `widgetkit_django*` package tree, including
`widgetkit_django.templatetags`, and includes its templates and static assets.
The host integration lives outside this distribution.

Remaining publication work is release management rather than package-boundary
work:

- choose a public versioning/release cadence and publish the wheel
- configure repository release automation
- decide whether duplicate placements need a separately versioned instance ID

Do not move host navigation, route names, domain resolution, persistence models,
sample data, or widget renderers into the reusable distribution.
