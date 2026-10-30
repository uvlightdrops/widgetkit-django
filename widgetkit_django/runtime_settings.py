"""Optional Django adapter for ki-core's framework-independent runtime editor."""
from __future__ import annotations

import json

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import select_template
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods


def _form_changes(request, snapshot):
    rows = {row["path"]: row for row in snapshot["rows"]}
    selected = request.POST.getlist("change")
    changes = {}
    for path in selected:
        row = rows.get(path)
        if row is None or not row["editable"]:
            raise ValueError
        raw = request.POST.get("value:" + path, "")
        changes[path] = raw if row["types"] == ["string"] and not row["enum"] else json.loads(raw)
    return changes, request.POST.getlist("remove")


def _display_rows(snapshot):
    for row in snapshot["rows"]:
        value = row["override"] if row["overridden"] else row["effective"]
        if row["types"] == ["string"] and not row["enum"]:
            row["input_value"] = "" if value is None else value
        else:
            row["input_value"] = json.dumps(value, ensure_ascii=False, allow_nan=False)
        row["enum_options"] = [
            {"value": json.dumps(v, ensure_ascii=False), "label": str(v),
             "selected": v == value} for v in row["enum"]
        ]
    return snapshot


def _compact_rows(rows):
    result, groups = [], set()
    for row in sorted(rows, key=lambda item: item["path"]):
        parts = row["path"].split(".")
        for depth in range(len(parts) - 1):
            path = ".".join(parts[:depth + 1])
            if path not in groups:
                groups.add(path)
                result.append({
                    "group": True, "path": path, "name": parts[depth],
                    "indent": depth * 14,
                })
        result.append({**row, "name": parts[-1], "indent": (len(parts) - 1) * 14})
    return result


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def runtime_settings_view(
    request, *, service, base_template="base.html", title="Konfiguration", context=None,
    compact=False,
):
    """Render a superuser-only editor; host supplies a fixed RuntimeSettings service.

    Form fields are ``revision``, repeated ``change`` / ``remove`` paths, and
    ``value:<path>``. Containers and union types use JSON; plain strings do not.
    JSON POSTs accept ``{revision, changes, remove}`` with the same CSRF policy.
    """
    from ki_core.runtime_settings import ConflictError, EditorError, ValidationError

    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.is_active and user.is_superuser):
        raise PermissionDenied
    status, error, saved = 200, None, request.GET.get("_settings_saved") == "1"
    snapshot = {"revision": "", "rows": []}
    secret_snapshot = {"revision": "", "rows": []}
    secret_error = None
    try:
        snapshot = service.snapshot()
        if request.method == "POST":
            action = request.POST.get("action") if request.content_type != "application/json" else None
            if action in ("save_secret", "remove_secret"):
                revision = request.POST.get("creds_revision", "")
                path = request.POST.get("secret_path", "")
                if action == "remove_secret":
                    if request.POST.get("confirm_remove") != "yes":
                        raise ValidationError("Löschen muss bestätigt werden.")
                    service.remove_secret(revision, path)
                else:
                    service.save_secret(revision, path, request.POST.get("secret_value", ""))
                snapshot = service.snapshot()
            elif request.content_type == "application/json":
                body = json.loads(request.body)
                revision, changes, remove = body["revision"], body.get("changes", {}), body.get("remove", [])
                snapshot = service.save(revision, changes, remove)
            else:
                revision = request.POST.get("revision", "")
                changes, remove = _form_changes(request, snapshot)
                snapshot = service.save(revision, changes, remove)
            saved = True
            if request.content_type != "application/json":
                query = request.GET.copy()
                query["_settings_saved"] = "1"
                return HttpResponseRedirect(request.path + "?" + query.urlencode())
    except ConflictError:
        status, error = 409, "Konfiguration wurde inzwischen geändert. Neu laden und erneut bearbeiten."
    except ValidationError:
        status, error = 400, "Ungültige Änderung; bitte Typ, Schema und Schreibrechte des Feldes prüfen."
    except EditorError:
        status, error = 400, "Konfiguration konnte nicht sicher gelesen oder gespeichert werden."
    except (ValueError, TypeError, KeyError):
        status, error = 400, "Ungültige Änderung; bitte Typ, Schema und Schreibrechte des Feldes prüfen."

    try:
        secret_snapshot = service.secret_snapshot()
    except EditorError:
        secret_error = "Zugangsdaten sind nicht projektlokal bearbeitbar (externes Ziel, Symlink oder ungültige Konfiguration). Bitte aktive creds.yaml direkt verwalten."

    base = select_template([base_template, "widgetkit_django/base.html"]).template.name
    payload = {
        **(context or {}), "widgetkit_base_template": base, "title": title,
        "snapshot": _display_rows(snapshot), "error": error, "saved": saved,
        "secret_snapshot": secret_snapshot, "secret_error": secret_error,
    }
    if compact:
        payload["compact_rows"] = _compact_rows(payload["snapshot"]["rows"])
        payload["compact_secret_rows"] = _compact_rows(secret_snapshot["rows"])
    template = "runtime_settings_compact.html" if compact else "runtime_settings.html"
    return render(request, "widgetkit_django/" + template, payload, status=status)
