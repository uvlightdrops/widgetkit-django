from types import SimpleNamespace

import pytest
import yaml
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-only", ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["testserver"],
        INSTALLED_APPS=["widgetkit_django"],
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True, "OPTIONS": {"context_processors": [
                "django.template.context_processors.csrf",
            ]},
        }],
    )
    import django
    django.setup()

from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory
from django.urls import path
from ki_core.runtime_settings import RuntimeSettings
from widgetkit_django.runtime_settings import runtime_settings_view

_service = None


def endpoint(request):
    permission = request.headers.get("X-Test-Permission", "admin")
    request.user = SimpleNamespace(
        is_authenticated=permission != "anonymous", is_active=permission != "inactive",
        is_superuser=permission == "admin",
    )
    return runtime_settings_view(
        request, service=_service, base_template="missing-host-base.html",
        context={"ownership_links": [{"url": "/owned-settings/", "label": "DB-Verwaltung"}]},
    )


urlpatterns = [path("settings/", endpoint)]


@pytest.fixture
def service(tmp_path, monkeypatch):
    global _service
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KI_STAGE", raising=False)
    monkeypatch.delenv("KI_PROFILE", raising=False)
    (tmp_path / "ki.yaml").write_text("ui:\n  name: lower\n")
    (tmp_path / "schema").mkdir()
    schema = {"type": "object", "properties": {"ui": {"type": "object", "properties": {
        "name": {"type": "string"}, "flag": {"type": "boolean", "default": False},
        "count": {"type": "integer", "minimum": 1, "default": 1},
        "list": {"type": "array", "items": {"type": "string"}, "default": []},
        "api_key": {"type": "string"},
    }}}}
    (tmp_path / "schema/ui.schema.yaml").write_text(yaml.safe_dump(schema))
    (tmp_path / "creds.yaml").write_text("ui:\n  api_key: never-echo-secret\n")
    _service = RuntimeSettings(tmp_path)
    yield _service
    _service = None


def test_authenticated_active_superuser_only(service):
    client = Client()
    for role in ("anonymous", "staff", "inactive"):
        assert client.get("/settings/", HTTP_X_TEST_PERMISSION=role).status_code == 403
        assert client.post("/settings/", HTTP_X_TEST_PERMISSION=role).status_code == 403
    assert client.get("/settings/").status_code == 200
    assert client.put("/settings/").status_code == 405


def test_get_redaction_revision_fallback_and_ownership_links(service):
    response = Client().get("/settings/")
    body = response.content.decode()
    assert response.status_code == 200
    assert 'name="revision"' in body
    assert "never-echo-secret" not in body
    assert "creds.yaml" in body
    assert "/owned-settings/" in body
    assert "DB-Verwaltung" in body
    assert "no-store" in response["Cache-Control"]
    assert "widgetkit" in body.lower() or "<!doctype html>" in body.lower()


def test_compact_view_hierarchy_assets_and_redaction(service):
    request = RequestFactory().get("/compact/")
    request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
    response = runtime_settings_view(
        request, service=service, compact=True, base_template="missing-host-base.html",
        context={"configuration_url": "/settings/"},
    )
    body = response.content.decode()
    assert response.status_code == 200
    assert 'class="wk-c2-table"' in body
    assert 'data-config-path="ui.name"' in body
    assert 'data-secret-path="ui.api_key"' in body
    assert "padding-left:14px" in body
    assert "runtime-settings-compact.css" in body
    assert "never-echo-secret" not in body


def test_compact_rows_keep_hierarchy_contiguous():
    from widgetkit_django.runtime_settings import _compact_rows

    rows = _compact_rows([{"path": "b.x"}, {"path": "a.y.z"}, {"path": "a.x"}])
    assert [row["path"] for row in rows] == ["a", "a.x", "a.y", "a.y.z", "b", "b.x"]
    assert [row["indent"] for row in rows] == [0, 14, 14, 28, 0, 14]


def test_csrf_required_for_post(service):
    client = Client(enforce_csrf_checks=True)
    response = client.get("/settings/")
    assert client.post("/settings/", {
        "revision": service.snapshot()["revision"], "change": ["ui.name"],
        "value:ui.name": "blocked",
    }).status_code == 403
    token = response.cookies["csrftoken"].value
    response = client.post("/settings/", {
        "csrfmiddlewaretoken": token, "revision": service.snapshot()["revision"],
        "change": ["ui.name", "ui.flag", "ui.count", "ui.list"],
        "value:ui.name": "saved", "value:ui.flag": "true", "value:ui.count": "3",
        "value:ui.list": '["one", "two"]',
    }, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain == [("/settings/?_settings_saved=1", 302)]
    assert b"Konfiguration gespeichert" in response.content
    rows = {r["path"]: r for r in service.snapshot()["rows"]}
    assert rows["ui.name"]["effective"] == "saved"
    assert rows["ui.flag"]["effective"] is True
    assert rows["ui.count"]["effective"] == 3
    assert rows["ui.list"]["effective"] == ["one", "two"]


def test_stale_revision_invalid_values_and_remove(service):
    client = Client()
    revision = service.snapshot()["revision"]
    service.save(revision, {"ui.name": "first"})
    assert client.post("/settings/", {
        "revision": revision, "change": ["ui.name"], "value:ui.name": "stale",
    }).status_code == 409
    assert client.post("/settings/", {
        "revision": service.snapshot()["revision"], "change": ["ui.count"],
        "value:ui.count": '"never-echo-invalid-value"',
    }).status_code == 400
    response = client.post("/settings/", {
        "revision": service.snapshot()["revision"], "change": ["ui.api_key"],
        "value:ui.api_key": "never-echo-submitted-secret",
    })
    assert response.status_code == 400
    assert b"never-echo-submitted-secret" not in response.content
    response = client.post("/settings/", {
        "revision": service.snapshot()["revision"], "remove": ["ui.name"],
    }, follow=True)
    assert response.status_code == 200
    assert {r["path"]: r for r in service.snapshot()["rows"]}["ui.name"]["effective"] == "lower"


def test_post_redirect_get_preserves_host_query_without_replaying_save(service):
    client = Client()
    response = client.post("/settings/?domain=alpha", {
        "revision": service.snapshot()["revision"], "change": ["ui.name"],
        "value:ui.name": "saved",
    })
    assert response.status_code == 302
    assert response["Location"] == "/settings/?domain=alpha&_settings_saved=1"
    revision = service.snapshot()["revision"]
    response = client.get(response["Location"])
    assert response.status_code == 200
    assert b"Konfiguration gespeichert" in response.content
    assert service.snapshot()["revision"] == revision


def test_secret_forms_write_only_csrf_prg_conflict_and_confirmed_removal(service):
    client = Client(enforce_csrf_checks=True)
    response = client.get("/settings/")
    csrf = response.cookies["csrftoken"].value
    revision = service.secret_snapshot()["revision"]
    payload = {
        "action": "save_secret", "creds_revision": revision,
        "secret_path": "ui.api_key", "secret_value": "synthetic-new-password",
    }
    assert client.post("/settings/", payload).status_code == 403
    response = client.post("/settings/", {**payload, "csrfmiddlewaretoken": csrf}, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain == [("/settings/?_settings_saved=1", 302)]
    assert b"synthetic-new-password" not in response.content
    assert b'type="password" name="secret_value"' in response.content
    assert b'data-secret-path="ui.api_key"' in response.content
    assert b"no-store" in response["Cache-Control"].encode()
    response = client.post("/settings/", {**payload, "csrfmiddlewaretoken": csrf})
    assert response.status_code == 409
    assert b"synthetic-new-password" not in response.content
    payload = {
        "csrfmiddlewaretoken": csrf, "action": "remove_secret",
        "creds_revision": service.secret_snapshot()["revision"], "secret_path": "ui.api_key",
    }
    assert client.post("/settings/", payload).status_code == 400
    assert {r["path"]: r for r in service.secret_snapshot()["rows"]}["ui.api_key"]["overridden"]
    response = client.post("/settings/", {**payload, "confirm_remove": "yes"}, follow=True)
    assert response.status_code == 200
    assert not {r["path"]: r for r in service.secret_snapshot()["rows"]}["ui.api_key"]["overridden"]


def test_secret_invalid_path_and_blank_never_echo(service):
    client = Client()
    revision = service.secret_snapshot()["revision"]
    for role in ("anonymous", "staff", "inactive"):
        assert client.post("/settings/", {
            "action": "save_secret", "creds_revision": revision,
            "secret_path": "ui.api_key", "secret_value": "synthetic-secret",
        }, HTTP_X_TEST_PERMISSION=role).status_code == 403
    response = client.post("/settings/", {
        "action": "save_secret", "creds_revision": revision,
        "secret_path": "ui.name", "secret_value": "never-echo-invalid-secret",
    })
    assert response.status_code == 400
    assert b"never-echo-invalid-secret" not in response.content
    response = client.post("/settings/", {
        "action": "save_secret", "creds_revision": revision,
        "secret_path": "ui.api_key", "secret_value": "",
    })
    assert response.status_code == 302
    assert service.secret_snapshot()["revision"] == revision
