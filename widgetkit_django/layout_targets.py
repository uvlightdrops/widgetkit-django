from __future__ import annotations

from urllib.parse import urlencode


_APP_AREAS = [
    {
        "key": "dashboard",
        "builder_area": "dashboard",
        "nav_key": "dashboard",
        "prefixes": ["/"],
        "submenu": [
            {"key": "overview", "label": "Overview", "path": "/", "description": "Zentrale Startseite des Arbeitsbereichs."},
        ],
    },
    {
        "key": "datasources",
        "builder_area": "datasources",
        "nav_key": "data-sources",
        "prefixes": ["/data-sources/"],
        "submenu": [
            {"key": "overview", "label": "Übersicht", "path": "/data-sources/", "description": "Discovery- und Import-Übersicht aller Quellen (Markdown, PDF, OWL, Jira)."},
            {"key": "sources", "label": "Sources", "path": "/data-sources/sources/", "description": "Quellen-Registry der aktiven Domain."},
            {"key": "workspace", "label": "Workspace", "path": "/data-sources/workspace/", "description": "Quellen vor dem Import prüfen, vorbereiten und importieren."},
            {"key": "pdf", "label": "PDF Import Jobs", "path": "/data-sources/pdf/", "description": "PDF-Batch-Import-Jobs und Verlauf."},
        ],
    },
    {
        "key": "knowledge",
        "builder_area": "knowledge",
        "nav_key": "internal-knowledge",
        "prefixes": ["/knowledge/"],
        "submenu": [
            {"key": "overview", "label": "Übersicht", "path": "/knowledge/", "description": "Verarbeitungs-Hub: Sources, Records, Artifacts."},
            {"key": "semantic", "label": "Semantic Layer", "path": "/knowledge/semantic/", "description": "Semantische Begriffe, Domain-Analyse und Konzeptgraph."},
            {"key": "terms", "label": "Domain Terms", "path": "/knowledge/semantic/terms/", "description": "Interne Begriffsliste zur Wissensmodellierung und Domain-Analyse."},
            {"key": "semantic-exclusions", "label": "Exclusion List", "path": "/knowledge/semantic/", "description": "Generische Stopword-/Ausschlussliste für Vorverarbeitung und Filterung."},
            {"key": "records", "label": "Records", "path": "/knowledge/records/", "description": "Records der aktiven Domain durchsuchen."},
            {"key": "artifacts", "label": "Artifacts", "path": "/knowledge/artifacts/", "description": "Generierte Artefakte und Zusammenfassungen."},
            {"key": "jobs", "label": "Jobs", "path": "/knowledge/jobs/", "description": "Hintergrund-Jobs und Sync-Verlauf."},
            {"key": "api", "label": "Knowledge API", "path": "/knowledge/api/", "description": "Knowledge-API-Browser und Health-Checks."},
            {"key": "support-chat", "label": "Support Chat", "path": "/knowledge/chat/support/", "description": "Domänen-übergreifender Support-Chat."},
            {"key": "ollama-chat", "label": "Ollama Chat", "path": "/knowledge/chat/ollama/", "description": "Lokaler LLM-Chat für Ad-hoc-Fragen."},
        ],
    },
    {
        "key": "infooutput",
        "builder_area": "infooutput",
        "nav_key": "info-output",
        "prefixes": ["/output/"],
        "submenu": [
            {"key": "overview", "label": "Übersicht", "path": "/output/", "description": "Alle Ausgabeformate im Überblick."},
            {"key": "infosite-dashboard", "label": "Infosite Dashboard", "path": "/output/infosite/dashboard/", "description": "Projekte, Generierung und AI-Refinement."},
            {"key": "quiz", "label": "Quiz (geplant)", "path": "/output/quiz/", "description": "Platzhalter für ein zukünftiges Quiz-Ausgabeformat — noch kein Konzept."},
        ],
    },
    {
        "key": "admin",
        "builder_area": "admin",
        "nav_key": "admin",
        "prefixes": ["/admin-overview/"],
        "submenu": [
            {"key": "overview", "label": "Übersicht", "path": "/admin-overview/", "description": "Zentrale Admin-Übersicht über Domains, Status und Systemwerte."},
            {"key": "domains", "label": "Domain Management", "path": "/admin-overview/domains/", "description": "Domains anlegen, Datenverzeichnisse scannen und verwalten."},
            {"key": "sync", "label": "Distributed Sync", "path": "/admin-overview/sync/", "description": "Node-Konfiguration, Master-Katalog und Sync-Historie verwalten."},
            {"key": "status", "label": "System Status", "path": "/admin-overview/status/", "description": "Anwendungsstatus und Laufzeitwerte prüfen."},
        ],
    },
    {
        "key": "settings",
        "builder_area": "settings",
        "nav_key": "settings",
        "prefixes": ["/settings/"],
        "submenu": [
            {"key": "overview", "label": "Übersicht", "path": "/settings/", "description": "Settings overview."},
            {"key": "config", "label": "Configuration", "path": "/settings/config/", "description": "Aktive AppConfig-Werte anzeigen."},
            {"key": "builder", "label": "Builder", "path": "/settings/layout/builder/", "description": "Widget-Layout pro Area verwalten."},
            {"key": "widgets", "label": "Widget catalog", "path": "/settings/layout/widgets/", "description": "Preview aller Widgets und ihres HTML-Codes."},
            {"key": "shell-builder", "label": "Widget shell builder", "path": "/settings/layout/shell-builder/", "description": "Widget-Shells ohne Live-Daten zusammenklicken."},
            {"key": "shells", "label": "Widget shell overview table", "path": "/settings/layout/shells/", "description": "Tabellarische Übersicht aller gespeicherten Widget-Shells."},
        ],
    },
]

_ACTIONS = [
    {
        "key": "cms-catalog",
        "nav_key": "cms-catalog",
        "prefixes": ["/cms/", "/cms-admin/", "/cms-documents/"],
        "submenu": [
            {"label": "Data Source Catalog", "url": "/cms/data-sources/", "description": "Editorial-Katalog der Datenquellen (Wagtail)."},
            {"label": "Knowledge Block Catalog", "url": "/cms/knowledge-blocks/", "description": "Editorial-Katalog der extrahierten Wissensblöcke (Wagtail)."},
            {"label": "Wagtail Admin", "url": "/cms-admin/", "description": "Wagtail-Administrationsoberfläche."},
        ],
    },
    {
        "key": "layout-builder",
        "nav_key": "layout-builder",
        "prefixes": ["/settings/layout/builder/", "/settings/layout/widgets/", "/settings/layout/shells/"],
        "submenu_source": "settings",
    },
]


def layout_targets_for_area(area_key: str) -> list[dict[str, str]]:
    normalized = (area_key or "dashboard").strip().lower()
    for area in _APP_AREAS:
        if area["builder_area"] == normalized:
            return [
                {"key": item["key"], "label": item["label"], "path": item["path"]}
                for item in area["submenu"]
                if item["key"] not in {"builder", "widgets", "shell-builder"}
            ]
    return [{"key": "overview", "label": "Overview", "path": "/"}]


def layout_target(area_key: str, subpage_key: str) -> dict[str, str]:
    normalized_subpage = (subpage_key or "overview").strip().lower() or "overview"
    for target in layout_targets_for_area(area_key):
        if target["key"] == normalized_subpage:
            return target
    return layout_targets_for_area(area_key)[0]


def layout_builder_url(area_key: str, subpage_key: str = "overview") -> str:
    return f"/settings/layout/builder/?{urlencode({'area': area_key, 'subpage': subpage_key})}"


def nav_areas_config() -> list[dict[str, object]]:
    areas: list[dict[str, object]] = []
    for area in _APP_AREAS:
        submenu = [(item["label"], item["path"], item["description"]) for item in area["submenu"]]
        areas.append({"key": area["nav_key"], "prefixes": list(area["prefixes"]), "submenu": submenu})
    for action in _ACTIONS:
        if action.get("submenu_source") == "settings":
            settings_area = next(area for area in _APP_AREAS if area["key"] == "settings")
            submenu = [(item["label"], item["path"], item["description"]) for item in settings_area["submenu"]]
        else:
            submenu = [(item["label"], item["url"], item["description"]) for item in action["submenu"]]
        areas.append({"key": action["nav_key"], "prefixes": list(action["prefixes"]), "submenu": submenu})
    return areas
